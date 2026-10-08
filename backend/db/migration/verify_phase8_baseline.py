"""Rehearse imported payments with a controlled provider in disposable MongoDB only."""
import hashlib
import hmac
import os
import re
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.config.security import create_access_token
from backend.db.migration.verify_phase5_baseline import main as verify_source
from backend.db.migration.verify_phase7_baseline import exercise_writes as exercise_quizzes, snapshot
from backend.db.mongo.quiz_schema import upgrade_quiz_receipts
from backend.db.mongo.payment_schema import upgrade_payment_intents
from backend.main import app


def prepare(database):
    upgrade_quiz_receipts(database)
    return upgrade_payment_intents(database)


def exercise_writes(database, source):
    if not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name):
        raise RuntimeError("Payment rehearsal requires a generated disposable target.")
    prior = exercise_quizzes(database, source)
    before = snapshot(database)
    course = database.courses.find_one({"is_published": True, "access_rule": "payment"})
    if course is None: raise RuntimeError("No original published payment course exists.")
    identities = list(database.users.find({"role": "learner"}))
    existing = {row["user_id"]: row for row in database.enrollments.find({"course_id": course["_id"]})}
    learner = next((row for row in identities if existing.get(row["_id"], {}).get("payment_status") not in {"paid", "not_required"}), None)
    if learner is None: raise RuntimeError("No original learner is eligible for the controlled payment rehearsal.")
    def bearer(user):
        return {"Authorization": "Bearer " + create_access_token({"sub": user["_id"], "email": user["email"], "role": user["role"]})}
    calls = []
    def create_order(**kwargs):
        calls.append(kwargs)
        return {"id": "order_phase8source1", "entity": "order", "amount": kwargs["amount_paise"],
            "currency": "INR", "receipt": kwargs["receipt"], "notes": kwargs["notes"], "status": "created"}
    def no_postgres(): raise AssertionError("MongoDB payment rehearsal must not fall back to PostgreSQL")
    with patch.dict(os.environ, {"RAZORPAY_KEY_ID": "synthetic_key", "RAZORPAY_KEY_SECRET": "synthetic_secret", "RAZORPAY_CURRENCY": "INR"}), \
            patch("backend.config.payments.create_razorpay_order", create_order), \
            patch("backend.modules.courses.service.connect", no_postgres), TestClient(app) as client:
        if app.state.courses_storage != "mongo" or app.state.mongo_settings.database != database.name:
            raise RuntimeError("The payment API is not using the disposable MongoDB target.")
        legacy_checks, paid_checks = 0, 0
        for member in before["enrollments"]:
            if member["payment_status"] not in {"paid", "not_required"}: continue
            legacy_course = database.courses.find_one({"_id": member["course_id"], "is_published": True})
            if legacy_course is None: continue
            user = database.users.find_one({"_id": member["user_id"]})
            if legacy_course["access_rule"] == "payment":
                response = client.post(f"/courses/{legacy_course['slug']}/payments/order", headers=bearer(user))
                valid = response.status_code == 200 and response.json() == {"alreadyPaid": True, "courseSlug": legacy_course["slug"]}
            else:
                response = client.get(f"/courses/{legacy_course['slug']}", headers=bearer(user))
                valid = response.status_code == 200 and response.json()["isEnrolled"]
            if not valid: raise RuntimeError("Imported authorized access was not retained.")
            legacy_checks += 1
            paid_checks += int(member["payment_status"] == "paid")
        if calls or snapshot(database) != before: raise RuntimeError("Legacy authorized checkout changed data or contacted the provider.")
        client.headers.update(bearer(learner))
        response = client.post(f"/courses/{course['slug']}/payments/order")
        if response.status_code != 200: raise RuntimeError("Imported learner's controlled checkout failed.")
        order = response.json()
        if order["amount"] != course["price_paise"] or order["currency"] != "INR" or len(order["receipt"]) > 40:
            raise RuntimeError("Checkout lost the source paise amount or currency.")
        provider_id, payment_id = order["orderId"], "pay_phase8source1"
        signature = hmac.new(b"synthetic_secret", f"{provider_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        payload = {"razorpayOrderId": provider_id, "razorpayPaymentId": payment_id, "razorpaySignature": signature}
        response = client.post(f"/courses/{course['slug']}/payments/verify", json=payload)
        if response.status_code != 200 or not response.json()["isEnrolled"] or response.json()["paymentStatus"] != "paid":
            raise RuntimeError("Controlled payment verification did not atomically unlock the source course.")
        committed = snapshot(database)
        replay = client.post(f"/courses/{course['slug']}/payments/verify", json=payload)
        if replay.status_code != 200 or replay.json() != response.json() or snapshot(database) != committed:
            raise RuntimeError("Repeated payment verification changed stored state.")
    user_id, course_id = learner["_id"], course["_id"]
    old_member = existing.get(user_id)
    new_member = database.enrollments.find_one({"course_id": course_id, "user_id": user_id})
    if old_member and any(new_member[key] != old_member[key] for key in ("_id", "enrolled_at", "enrollment_source")):
        raise RuntimeError("Payment replaced an imported membership identity/date/source.")
    previous_orders = {row["_id"] for row in before["payment_orders"]}
    previous_intents = {row["_id"] for row in before["payment_checkout_intents"]}
    for name, rows in before.items():
        actual = list(database[name].find().sort("_id", 1))
        if name == "payment_orders": actual = [row for row in actual if row["_id"] in previous_orders]
        elif name == "payment_checkout_intents": actual = [row for row in actual if row["_id"] in previous_intents]
        elif name == "enrollments":
            rows = [row for row in rows if not (row["course_id"] == course_id and row["user_id"] == user_id)]
            actual = [row for row in actual if not (row["course_id"] == course_id and row["user_id"] == user_id)]
        elif name == "courses":
            rows = [{key: value for key, value in row.items() if not (row["_id"] == course_id and key == "updated_at")} for row in rows]
            actual = [{key: value for key, value in row.items() if not (row["_id"] == course_id and key == "updated_at")} for row in actual]
        if rows != actual: raise RuntimeError("Controlled payment rehearsal changed unrelated data: " + name)
    if len(calls) != 1: raise RuntimeError("Payment rehearsal repeated provider order creation.")
    return {"phase7": prior, "controlled_provider_orders_created": 1, "payment_verifications": 1,
        "identical_verification_replays": 1, "legacy_authorized_memberships_preserved": legacy_checks,
        "legacy_paid_memberships_checked": paid_checks,
        "untargeted_records_unchanged": True, "actual_hmac_verified": True, "live_provider_calls": 0,
        "postgres_write_baseline_exercised": False}


if __name__ == "__main__":
    verify_source("phase8", exercise=exercise_writes, prepare=prepare)
