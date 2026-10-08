"""Phase 8 real MongoDB transactions with controlled providers; never live checkout."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import hmac
from uuid import uuid4

from fastapi import HTTPException
from pymongo.errors import OperationFailure, WriteError
import pytest

from backend.config import payments as provider
from backend.db.migration.reconcile_payment_intent import reconcile
from backend.db.mongo.init_db import initialize_database, SchemaDriftError
from backend.db.mongo.payment_schema import EXTENSION_ID, require_payment_intents, upgrade_payment_intents
from backend.db.mongo.quiz_schema import upgrade_quiz_receipts
from backend.db.mongo.seed import fixture_id
from backend.modules.courses.mongo_service import MongoCourseService
from backend.tests.test_mongo_courses import courses, learner, learner_http, enrollment
from backend.tests.test_mongo_progress_reviews import snapshot, synchronize


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "test_key")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "synthetic_phase8_secret")
    monkeypatch.setenv("RAZORPAY_CURRENCY", "INR")
    calls, orders = [], {}
    def create(**kwargs):
        from pymongo import _csot
        assert _csot.get_timeout() is None, "Provider network segment must not inherit a MongoDB deadline"
        calls.append(deepcopy(kwargs))
        order = {"id": "order_test" + str(len(calls)), "entity": "order", "amount": kwargs["amount_paise"],
                 "currency": "INR", "receipt": kwargs["receipt"], "notes": kwargs["notes"], "status": "created"}
        orders[order["id"]] = deepcopy(order)
        return order
    monkeypatch.setattr(provider, "create_razorpay_order", create)
    return {"calls": calls, "orders": orders, "create": create}


@pytest.fixture
def payment_ready(database):
    upgrade_quiz_receipts(database)
    upgrade_payment_intents(database)
    return database


def signed(order_id="order_test1", payment_id="pay_test1"):
    signature = hmac.new(b"synthetic_phase8_secret", f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return {"razorpayOrderId": order_id, "razorpayPaymentId": payment_id, "razorpaySignature": signature}


def test_payment_schema_preserves_domains_and_all_prior_migrations(database):
    upgrade_quiz_receipts(database)
    before = snapshot(database)
    first = upgrade_payment_intents(database)
    assert first["collections"] == 17 and first["named_indexes"] == 30
    assert first["domain_records_rewritten"] == 0
    after = snapshot(database)
    assert all(before[name] == after[name] for name in before if name != "schema_migrations")
    assert upgrade_payment_intents(database) == first and snapshot(database) == after
    assert initialize_database(database)["collections"] == 17
    upgrade_quiz_receipts(database)
    assert snapshot(database) == after


def test_payment_migration_requires_quiz_extension(database):
    before = snapshot(database)
    with pytest.raises(HTTPException): upgrade_payment_intents(database)
    assert snapshot(database) == before


@pytest.mark.parametrize("drift", ["collection", "index", "validator", "ledger"])
def test_payment_schema_stops_unknown_drift_before_ddl(database, drift):
    upgrade_quiz_receipts(database)
    if drift == "collection": database.create_collection("unmanaged")
    elif drift == "index": database.reviews.create_index("rating", name="unexpected")
    elif drift == "validator": database.command({"collMod": "reviews", "validationLevel": "moderate"})
    else: database.schema_migrations.update_one({}, {"$set": {"checksum": "wrong"}})
    before = snapshot(database)
    with pytest.raises((SchemaDriftError, HTTPException)): upgrade_payment_intents(database)
    assert snapshot(database) == before and "payment_checkout_intents" not in database.list_collection_names()


def test_payment_schema_recovers_interrupted_collection_creation(database, monkeypatch):
    upgrade_quiz_receipts(database)
    kind = type(database.schema_migrations)
    original = kind.update_one
    def fail_ledger(collection, query, *args, **kwargs):
        if collection.name == "schema_migrations" and query.get("_id") == EXTENSION_ID:
            raise RuntimeError("interrupt before ledger")
        return original(collection, query, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(kind, "update_one", fail_ledger)
        with pytest.raises(RuntimeError): upgrade_payment_intents(database)
    with pytest.raises(SchemaDriftError): initialize_database(database)
    upgrade_payment_intents(database)
    require_payment_intents(database)
    assert initialize_database(database)["named_indexes"] == 30


def test_order_api_stores_exact_amount_and_preserves_pending_membership(payment_ready, learner_http, database, fake_provider):
    previous = enrollment(database, "payment", "pending", "invited")
    response = learner_http.post("/courses/demo-payment/payments/order")
    assert response.status_code == 200
    result = response.json()
    assert result["amount"] == 9900 and result["currency"] == "INR" and result["keyId"] == "test_key"
    assert len(result["receipt"]) == 36 and result["receipt"].startswith("lnv-")
    order = database.payment_orders.find_one()
    intent = database.payment_checkout_intents.find_one()
    assert order["status"] == "created" and order["provider_order_id"] == result["orderId"]
    assert order["receipt"] == intent["receipt"] and intent["status"] == "persisted"
    member = database.enrollments.find_one()
    for field in ("_id", "enrolled_at", "enrollment_source"): assert member[field] == previous[field]
    assert member["payment_status"] == "pending" and len(fake_provider["calls"]) == 1
    second = learner_http.post("/courses/demo-payment/payments/order").json()
    assert second["receipt"] != result["receipt"] and second["orderId"] != result["orderId"]


@pytest.mark.parametrize("payment", ["paid", "not_required"])
def test_legacy_authorized_access_needs_no_order_or_gateway_config(payment_ready, courses, database, learner, fake_provider, monkeypatch, payment):
    enrollment(database, "payment", payment, "admin_added")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "")
    before = snapshot(database)
    assert courses.create_course_payment_order("demo-payment", learner) == {"alreadyPaid": True, "courseSlug": "demo-payment"}
    assert snapshot(database) == before and not fake_provider["calls"]


@pytest.mark.parametrize("problem,status", [("missing", 404), ("unpublished", 404), ("free", 400), ("invitation", 400),
                                          ("unknown_user", 404), ("configuration", 503)])
def test_checkout_preflight_rejects_without_provider_call(payment_ready, courses, database, learner, fake_provider, monkeypatch, problem, status):
    slug = "demo-payment"
    if problem == "missing": slug = "missing"
    elif problem == "unpublished": database.courses.update_one({"slug": slug}, {"$set": {"is_published": False}})
    elif problem == "free": slug = "demo-open"
    elif problem == "invitation": database.courses.update_one({"slug": slug}, {"$set": {"access_rule": "invitation"}})
    elif problem == "unknown_user": learner = {**learner, "id": str(uuid4())}
    else: monkeypatch.setenv("RAZORPAY_KEY_SECRET", "")
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: courses.create_course_payment_order(slug, learner)
    assert failure.value.status_code == status and snapshot(database) == before and not fake_provider["calls"]


@pytest.mark.parametrize("error", [TimeoutError("private upstream details"), HTTPException(502, "secret provider body")])
def test_provider_error_retains_safe_intent_without_pending_access(payment_ready, learner_http, database, monkeypatch, error):
    def fail(**kwargs): raise error
    monkeypatch.setattr(provider, "create_razorpay_order", fail)
    response = learner_http.post("/courses/demo-payment/payments/order", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 502 and "private" not in response.text and "secret" not in response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    intent = database.payment_checkout_intents.find_one()
    assert intent["status"] == "uncertain" and intent["failure_code"] == "provider_error"
    assert not database.payment_orders.find_one() and not database.enrollments.find_one()


@pytest.mark.parametrize("problem", ["amount", "currency", "receipt", "user", "course", "intent", "id", "entity"])
def test_malformed_provider_orders_cannot_create_access(payment_ready, courses, database, learner, fake_provider, monkeypatch, problem):
    def malformed(**kwargs):
        order = fake_provider["create"](**kwargs)
        if problem in {"user", "course", "intent"}:
            field = {"user": "user_id", "course": "course_id", "intent": "checkout_intent_id"}[problem]
            order["notes"][field] = "other"
        else: order[problem] = {"amount": 1, "currency": "USD", "receipt": "other", "id": "invalid", "entity": "payment"}[problem]
        return order
    monkeypatch.setattr(provider, "create_razorpay_order", malformed)
    with pytest.raises(HTTPException) as failure: courses.create_course_payment_order("demo-payment", learner)
    assert failure.value.status_code == 502
    assert not database.payment_orders.find_one() and not database.enrollments.find_one()
    assert database.payment_checkout_intents.find_one()["status"] == "uncertain"


@pytest.mark.parametrize("collection", ["payment_orders", "enrollments", "payment_checkout_intents"])
def test_order_persistence_failure_rolls_back_and_reconciles(payment_ready, courses, database, learner, fake_provider, monkeypatch, collection):
    kind = type(database.payment_orders)
    method = "insert_one" if collection == "payment_orders" else "update_one"
    original = getattr(kind, method)
    def fail(target, *args, **kwargs):
        result = original(target, *args, **kwargs)
        if target.name == collection and kwargs.get("session") is not None:
            # Intent creation uses insert_one, so only final persistence is injected here.
            raise HTTPException(503, "injected database failure")
        return result
    with monkeypatch.context() as patch:
        patch.setattr(kind, method, fail)
        with pytest.raises(HTTPException) as failure: courses.create_course_payment_order("demo-payment", learner)
        assert failure.value.status_code == 503
    intent = database.payment_checkout_intents.find_one()
    assert intent["status"] == "uncertain" and not database.payment_orders.find_one() and not database.enrollments.find_one()
    before = snapshot(database)
    fetch = lambda identifier: fake_provider["orders"][identifier]
    dry = reconcile(database, intent["_id"], "order_test1", fetch_order=fetch)
    assert not dry["applied"] and snapshot(database) == before
    result = reconcile(database, intent["_id"], "order_test1", apply=True, fetch_order=fetch)
    assert result["applied"] and not result["paid_access_granted"]
    assert database.enrollments.find_one()["payment_status"] == "pending"
    assert database.payment_orders.count_documents({}) == 1
    reconcile(database, intent["_id"], "order_test1", apply=True, fetch_order=fetch)
    assert database.payment_orders.count_documents({}) == 1 and len(fake_provider["calls"]) == 1


def test_transient_persistence_retry_never_repeats_provider_call(payment_ready, courses, database, learner, fake_provider, monkeypatch):
    kind, seen = type(database.payment_orders), []
    original = kind.insert_one
    def transient(collection, document, *args, **kwargs):
        result = original(collection, document, *args, **kwargs)
        if collection.name == "payment_orders":
            seen.append(document["_id"])
            if len(seen) == 1:
                raise OperationFailure("retry", code=112, details={"errorLabels": ["TransientTransactionError"]})
        return result
    monkeypatch.setattr(kind, "insert_one", transient)
    result = courses.create_course_payment_order("demo-payment", learner)
    assert result["orderId"] == "order_test1" and len(fake_provider["calls"]) == 1
    assert len(seen) == 2 and len(set(seen)) == 1 and database.payment_orders.count_documents({}) == 1


@pytest.mark.parametrize("change", ["paid_access", "price", "publication", "deletion", "access_rule"])
def test_checkout_revalidates_after_provider_call(payment_ready, courses, database, learner, fake_provider, monkeypatch, change):
    def create(**kwargs):
        order = fake_provider["create"](**kwargs)
        if change == "paid_access": enrollment(database, "payment", "paid", "admin_added")
        elif change == "deletion": database.courses.delete_one({"slug": "demo-payment"})
        else: database.courses.update_one({"slug": "demo-payment"}, {"$set": {
            "price": {"price_paise": 10000}, "publication": {"is_published": False},
            "access_rule": {"access_rule": "invitation"}}[change]})
        return order
    monkeypatch.setattr(provider, "create_razorpay_order", create)
    if change == "paid_access":
        assert courses.create_course_payment_order("demo-payment", learner)["alreadyPaid"]
        assert database.enrollments.find_one()["payment_status"] == "paid"
    else:
        with pytest.raises(HTTPException) as failure: courses.create_course_payment_order("demo-payment", learner)
        assert failure.value.status_code == 409
        assert not database.payment_orders.find_one() and not database.enrollments.find_one()
        assert database.payment_checkout_intents.find_one()["status"] == "conflict"


def test_verification_http_replay_preserves_order_and_membership(payment_ready, learner_http, database):
    order = learner_http.post("/courses/demo-payment/payments/order").json()
    before = database.enrollments.find_one()
    payload = signed(order["orderId"])
    response = learner_http.post("/courses/demo-payment/payments/verify", json=payload)
    assert response.status_code == 200 and response.json()["isEnrolled"] and response.json()["paymentStatus"] == "paid"
    member = database.enrollments.find_one()
    assert member["_id"] == before["_id"] and member["enrolled_at"] == before["enrolled_at"]
    saved = snapshot(database)
    replay = learner_http.post("/courses/demo-payment/payments/verify", json=payload)
    assert replay.status_code == 200 and replay.json() == response.json() and snapshot(database) == saved


@pytest.mark.parametrize("problem,status", [("signature", 400), ("unicode_signature", 400), ("unknown_order", 404), ("wrong_course", 404),
                                          ("wrong_user", 404), ("changed_payment", 409)])
def test_invalid_verification_cannot_grant_or_replace_access(payment_ready, courses, database, learner, problem, status):
    order = courses.create_course_payment_order("demo-payment", learner)
    payload, slug = signed(order["orderId"]), "demo-payment"
    if problem == "signature": payload["razorpaySignature"] = "invalid"
    elif problem == "unicode_signature": payload["razorpaySignature"] = "\u00e9" * 64
    elif problem == "unknown_order": payload = signed("order_other")
    elif problem == "wrong_course": slug = "demo-open"
    elif problem == "wrong_user": learner = {**learner, "id": fixture_id("instructor")}
    else:
        courses.verify_course_payment(slug, learner, payload)
        payload = signed(order["orderId"], "pay_other")
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: courses.verify_course_payment(slug, learner, payload)
    assert failure.value.status_code == status and snapshot(database) == before


@pytest.mark.parametrize("stage", ["order", "enrollment", "response"])
def test_verification_failure_rolls_back_paid_state(payment_ready, courses, database, learner, monkeypatch, stage):
    order = courses.create_course_payment_order("demo-payment", learner)
    before = snapshot(database)
    if stage == "response":
        def fail(*args, **kwargs): raise HTTPException(503, "response failed")
        monkeypatch.setattr(courses, "_detail", fail)
    else:
        kind = type(database.payment_orders)
        original = kind.update_one
        target = "payment_orders" if stage == "order" else "enrollments"
        def fail(collection, *args, **kwargs):
            result = original(collection, *args, **kwargs)
            if collection.name == target: raise HTTPException(503, "write failed")
            return result
        monkeypatch.setattr(kind, "update_one", fail)
    with pytest.raises(HTTPException): courses.verify_course_payment("demo-payment", learner, signed(order["orderId"]))
    assert snapshot(database) == before


@pytest.mark.parametrize("same_payment", [True, False])
def test_concurrent_verification_keeps_one_payment_identity(payment_ready, courses, database, learner, monkeypatch, same_payment):
    order = courses.create_course_payment_order("demo-payment", learner)
    other = MongoCourseService(database)
    synchronize(monkeypatch, courses, other)
    def verify(service, payment):
        try:
            return service.verify_course_payment("demo-payment", learner, signed(order["orderId"], payment))["isEnrolled"]
        except HTTPException as error: return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(verify, courses, "pay_test1")
        b = pool.submit(verify, other, "pay_test1" if same_payment else "pay_other")
        results = [a.result(), b.result()]
    assert results == [True, True] if same_payment else sorted(results) == [True, 409]
    assert database.payment_orders.count_documents({"status": "paid"}) == 1
    assert database.enrollments.count_documents({"payment_status": "paid"}) == 1


def test_payment_id_cannot_be_attached_to_another_order(payment_ready, courses, database, learner):
    first = courses.create_course_payment_order("demo-payment", learner)
    second = courses.create_course_payment_order("demo-payment", learner)
    courses.verify_course_payment("demo-payment", learner, signed(first["orderId"]))
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: courses.verify_course_payment("demo-payment", learner, signed(second["orderId"]))
    assert failure.value.status_code == 409 and snapshot(database) == before


def test_payment_api_never_uses_postgres(payment_ready, learner_http, monkeypatch):
    def fail(): raise AssertionError("No PostgreSQL fallback")
    monkeypatch.setattr("backend.modules.courses.service.connect", fail)
    response = learner_http.post("/courses/demo-payment/payments/order")
    assert response.status_code == 200
    response = learner_http.post("/courses/demo-payment/payments/verify", json=signed(response.json()["orderId"]))
    assert response.status_code == 200 and response.json()["isEnrolled"]


def test_lost_provider_response_recovers_from_durable_receipt(payment_ready, courses, database, learner, fake_provider, monkeypatch):
    def uncertain(**kwargs):
        fake_provider["create"](**kwargs)
        raise TimeoutError("response lost after provider creation")
    monkeypatch.setattr(provider, "create_razorpay_order", uncertain)
    with pytest.raises(HTTPException): courses.create_course_payment_order("demo-payment", learner)
    intent = database.payment_checkout_intents.find_one()
    assert "provider_order_id" not in intent and intent["status"] == "uncertain"
    assert intent["receipt"] == fake_provider["orders"]["order_test1"]["receipt"]
    reconcile(database, intent["_id"], "order_test1", apply=True, fetch_order=lambda key: fake_provider["orders"][key])
    assert database.enrollments.find_one()["payment_status"] == "pending" and len(fake_provider["calls"]) == 1


def test_database_outage_after_provider_success_retains_prepared_intent(payment_ready, courses, database, learner, fake_provider, monkeypatch):
    original = courses._payment_db
    def create(**kwargs):
        order = fake_provider["create"](**kwargs)
        def unavailable(callback): raise HTTPException(503, "database unavailable")
        monkeypatch.setattr(courses, "_payment_db", unavailable)
        return order
    monkeypatch.setattr(provider, "create_razorpay_order", create)
    with pytest.raises(HTTPException) as failure: courses.create_course_payment_order("demo-payment", learner)
    assert failure.value.status_code == 503
    intent = database.payment_checkout_intents.find_one()
    assert intent["status"] == "prepared" and not database.payment_orders.find_one() and not database.enrollments.find_one()
    monkeypatch.setattr(courses, "_payment_db", original)
    reconcile(database, intent["_id"], "order_test1", apply=True, fetch_order=lambda key: fake_provider["orders"][key])
    assert database.payment_orders.count_documents({}) == 1


def test_reconciliation_refuses_foreign_provider_binding(payment_ready, courses, database, learner, fake_provider):
    courses.create_course_payment_order("demo-payment", learner)
    intent = database.payment_checkout_intents.find_one()
    foreign = deepcopy(fake_provider["orders"]["order_test1"])
    foreign["notes"]["user_id"] = fixture_id("instructor")
    before = snapshot(database)
    with pytest.raises(HTTPException):
        reconcile(database, intent["_id"], "order_test1", apply=True, fetch_order=lambda key: foreign)
    assert snapshot(database) == before


def test_actual_validator_rejection_rolls_back_paid_access(payment_ready, courses, database, learner, monkeypatch):
    order = courses.create_course_payment_order("demo-payment", learner)
    before = snapshot(database)
    kind, original = type(database.payment_orders), type(database.payment_orders).update_one
    def invalid(collection, query, update, *args, **kwargs):
        if collection.name == "payment_orders":
            update = deepcopy(update)
            update["$set"]["verified_at"] = "invalid date"
        return original(collection, query, update, *args, **kwargs)
    monkeypatch.setattr(kind, "update_one", invalid)
    with pytest.raises(HTTPException) as failure: courses.verify_course_payment("demo-payment", learner, signed(order["orderId"]))
    assert failure.value.status_code == 422 and snapshot(database) == before


def test_checkout_cannot_downgrade_concurrent_payment_verification(payment_ready, courses, database, learner, fake_provider, monkeypatch):
    first = courses.create_course_payment_order("demo-payment", learner)
    def create(**kwargs):
        order = fake_provider["create"](**kwargs)
        courses.verify_course_payment("demo-payment", learner, signed(first["orderId"]))
        return order
    monkeypatch.setattr(provider, "create_razorpay_order", create)
    assert courses.create_course_payment_order("demo-payment", learner)["alreadyPaid"]
    assert database.enrollments.find_one()["payment_status"] == "paid"
    assert database.payment_orders.find_one({"provider_order_id": first["orderId"]})["status"] == "paid"


def test_slow_provider_receives_fresh_database_budget(payment_ready, courses, learner, fake_provider, monkeypatch):
    import time
    import pymongo
    original = courses._payment_db
    def bounded(callback):
        with pymongo.timeout(0.5): return original(callback)
    monkeypatch.setattr(courses, "_payment_db", bounded)
    def slow(**kwargs):
        time.sleep(0.6)  # Longer than each isolated database segment's deadline.
        return fake_provider["create"](**kwargs)
    monkeypatch.setattr(provider, "create_razorpay_order", slow)
    assert courses.create_course_payment_order("demo-payment", learner)["orderId"] == "order_test1"


def test_verification_and_course_deletion_leave_no_orphans(payment_ready, courses, database, learner, monkeypatch):
    from backend.modules.admin.mongo_service import MongoAdminService
    order = courses.create_course_payment_order("demo-payment", learner)
    admin = MongoAdminService(database)
    synchronize(monkeypatch, courses, admin)
    def verify():
        try: return courses.verify_course_payment("demo-payment", learner, signed(order["orderId"]))["isEnrolled"]
        except HTTPException as error: return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        writing = pool.submit(verify)
        deletion = pool.submit(admin.delete_admin_course, "demo-payment")
        assert deletion.result()["deleted"] and writing.result() in (True, 404)
    assert not database.payment_orders.find_one() and not database.enrollments.find_one()
    assert database.payment_checkout_intents.count_documents({}) == 1  # Operational recovery audit is retained.


def test_changed_payment_schema_readiness_creates_no_provider_effect(payment_ready, courses, database, learner, fake_provider):
    database.schema_migrations.update_one({"_id": EXTENSION_ID}, {"$set": {"checksum": "unknown"}})
    before = snapshot(database)
    with pytest.raises(HTTPException) as failure: courses.create_course_payment_order("demo-payment", learner)
    assert failure.value.status_code == 503 and snapshot(database) == before and not fake_provider["calls"]


def test_provider_fetch_is_read_only_and_sanitizes_errors(monkeypatch):
    import json
    from urllib.error import URLError
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps({"id": "order_test1"}).encode()
    def fetch(request, timeout):
        calls.append((request.get_method(), request.full_url, timeout))
        return Response()
    monkeypatch.setattr(provider.request, "urlopen", fetch)
    assert provider.fetch_razorpay_order("order_test1")["id"] == "order_test1"
    assert calls == [("GET", provider.RAZORPAY_ORDER_URL + "/order_test1", 20)]
    def fail(*args, **kwargs): raise URLError("private provider body")
    monkeypatch.setattr(provider.request, "urlopen", fail)
    with pytest.raises(HTTPException) as failure: provider.fetch_razorpay_order("order_test1")
    assert failure.value.status_code == 502 and "private" not in failure.value.detail


def test_numeric_provider_order_id_is_safely_recorded_as_uncertain(payment_ready, courses, database, learner, fake_provider, monkeypatch):
    def malformed(**kwargs):
        return {**fake_provider["create"](**kwargs), "id": 123}
    monkeypatch.setattr(provider, "create_razorpay_order", malformed)
    with pytest.raises(HTTPException) as failure: courses.create_course_payment_order("demo-payment", learner)
    assert failure.value.status_code == 502
    intent = database.payment_checkout_intents.find_one()
    assert intent["status"] == "uncertain" and "provider_order_id" not in intent
    assert not database.payment_orders.find_one() and not database.enrollments.find_one()
