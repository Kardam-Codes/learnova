"""MongoDB checkout persistence with durable recovery around external provider calls."""
from datetime import datetime, timezone
import logging
import re
from uuid import uuid4

from fastapi import HTTPException

from backend.config import payments as provider
from backend.db.mongo.payment_schema import require_payment_intents
from backend.db.mongo.transactions import lock_course

logger = logging.getLogger(__name__)


def now():
    return datetime.now(timezone.utc)


def authorized(enrollment):
    return bool(enrollment and enrollment["payment_status"] in {"paid", "not_required"})


def validate_provider_order(order, intent):
    notes = order.get("notes") if isinstance(order, dict) else None
    if (not isinstance(order, dict) or not isinstance(order.get("id"), str)
            or not re.fullmatch(r"order_[A-Za-z0-9]+", order["id"])
            or order.get("entity") != "order" or type(order.get("amount")) is not int
            or order["amount"] != intent["amount_paise"] or order.get("currency") != intent["currency"]
            or order.get("receipt") != intent["receipt"] or not isinstance(notes, dict)
            or any(notes.get(key) != intent[field] for key, field in (
                ("user_id", "user_id"), ("course_id", "course_id"), ("checkout_intent_id", "_id")))):
        raise HTTPException(502, "Payment provider returned an inconsistent order.")


class MongoPaymentService:
    def __init__(self, courses):
        self.courses = courses
        self.database = courses.database

    def db(self, callback):
        # Every segment has its own finite MongoDB deadline; provider I/O is outside it.
        return self.courses._payment_db(callback)

    def _user(self, identifier, session):
        row = self.database.users.find_one({"_id": identifier}, session=session)
        if row is None:
            raise HTTPException(404, "User not found.")
        return row

    def _prepare(self, course_slug, user, identifier, stamp):
        def prepare(session):
            require_payment_intents(self.database, session)
            course = self.courses._course(course_slug, session)
            self._user(user["id"], session)
            if course["access_rule"] != "payment":
                raise HTTPException(400, "This course does not require a payment checkout.")
            if authorized(self.courses._enrollment(course["_id"], user["id"], session)):
                return {"alreadyPaid": True, "courseSlug": course_slug}
            settings = provider.ensure_razorpay_configured()
            if not isinstance(course["price_paise"], int) or isinstance(course["price_paise"], bool) or course["price_paise"] <= 0:
                raise HTTPException(400, "The course has no valid payment price.")
            lock_course(self.database, course["_id"], session)
            intent = {"_id": identifier, "schema_version": 1, "course_id": course["_id"],
                "course_slug": course_slug, "user_id": user["id"], "amount_paise": course["price_paise"],
                "currency": settings.currency, "receipt": "lnv-" + identifier.replace("-", ""),
                "status": "prepared", "created_at": stamp, "updated_at": stamp}
            self.database.payment_checkout_intents.insert_one(intent, session=session)
            return intent
        return self.db(lambda: self.courses._transaction(prepare))

    def _record(self, intent, status, failure=None, order_id=None):
        fields = {"status": status, "updated_at": now()}
        if failure: fields["failure_code"] = failure
        if isinstance(order_id, str) and re.fullmatch(r"order_[A-Za-z0-9]+", order_id): fields["provider_order_id"] = order_id
        self.db(lambda: self.database.payment_checkout_intents.update_one({"_id": intent["_id"],
            "status": {"$ne": "persisted"}}, {"$set": fields}))

    def _recoverable_failure(self, intent, status, failure, order_id=None):
        # Never log credentials, signatures, payload bodies, or provider exception text.
        logger.warning("Payment checkout needs reconciliation intent=%s receipt=%s provider_order=%s code=%s",
                       intent["_id"], intent["receipt"], order_id if isinstance(order_id, str) and
                       re.fullmatch(r"order_[A-Za-z0-9]+", order_id) else "unknown", failure)
        try:
            self._record(intent, status, failure, order_id)
        except Exception:
            # The durable prepared intent still correlates a provider/dashboard lookup.
            logger.warning("Payment intent update unavailable intent=%s", intent["_id"])

    def create_order(self, course_slug, user):
        intent = self._prepare(course_slug, user, str(uuid4()), now())
        if intent.get("alreadyPaid"): return intent
        try:
            order = provider.create_razorpay_order(amount_paise=intent["amount_paise"], receipt=intent["receipt"], notes={
                "user_id": intent["user_id"], "course_id": intent["course_id"], "checkout_intent_id": intent["_id"]})
        except Exception as error:
            self._recoverable_failure(intent, "uncertain", "provider_error")
            status = 503 if isinstance(error, HTTPException) and error.status_code == 503 else 502
            raise HTTPException(status, "Payment order could not be created. Reference: " + intent["_id"]) from None
        order_id = order.get("id") if isinstance(order, dict) else None
        try:
            validate_provider_order(order, intent)
        except HTTPException as error:
            self._recoverable_failure(intent, "uncertain", "provider_response_invalid", order_id)
            raise HTTPException(error.status_code, "Payment order could not be confirmed. Reference: " + intent["_id"]) from None
        try:
            self._record(intent, "provider_created", order_id=order_id)
            return self.persist_order(intent["_id"], order)
        except Exception as error:
            conflict = isinstance(error, HTTPException) and error.status_code in {404, 409}
            self._recoverable_failure(intent, "conflict" if conflict else "uncertain",
                                      "terms_changed" if conflict else "persistence_error", order_id)
            raise HTTPException(409 if conflict else 503,
                "Payment checkout needs reconciliation. Reference: " + intent["_id"]) from None

    def persist_order(self, intent_id, order):
        order_id, enrollment_id, stamp = str(uuid4()), str(uuid4()), now()
        def persist(session):
            require_payment_intents(self.database, session)
            intent = self.database.payment_checkout_intents.find_one({"_id": intent_id}, session=session)
            if intent is None: raise HTTPException(404, "Payment checkout intent was not found.")
            validate_provider_order(order, intent)
            if intent.get("provider_order_id") not in (None, order["id"]):
                raise HTTPException(409, "The checkout intent is bound to a different provider order.")
            course = lock_course(self.database, intent["course_id"], session)
            if (not course["is_published"] or course["slug"] != intent["course_slug"]
                    or course["access_rule"] != "payment" or course["price_paise"] != intent["amount_paise"]):
                raise HTTPException(409, "Course payment terms changed during checkout.")
            learner = self._user(intent["user_id"], session)
            query = {"course_id": course["_id"], "user_id": learner["_id"]}
            stored = self.database.payment_orders.find_one({"provider_order_id": order["id"]}, session=session)
            if stored is not None:
                if any(stored.get(key) != value for key, value in {**query, "amount_paise": intent["amount_paise"],
                        "currency": intent["currency"], "receipt": intent["receipt"], "provider": "razorpay"}.items()):
                    raise HTTPException(409, "The provider order belongs to another checkout.")
            else:
                self.database.payment_orders.insert_one({"_id": order_id, "schema_version": 1, **query,
                    "provider": "razorpay", "provider_order_id": order["id"], "amount_paise": intent["amount_paise"],
                    "currency": intent["currency"], "receipt": intent["receipt"], "status": "created",
                    "created_at": intent["created_at"], "verified_at": None}, session=session)
            member = self.courses._enrollment(course["_id"], learner["_id"], session)
            already_paid = authorized(member)
            if not already_paid:
                self.database.enrollments.update_one(query, {"$set": {"payment_status": "pending"},
                    "$setOnInsert": {"_id": enrollment_id, "schema_version": 1, "enrolled_at": stamp,
                                     "enrollment_source": "self"}}, upsert=True, session=session)
            self.database.payment_checkout_intents.update_one({"_id": intent_id}, {"$set": {
                "status": "persisted", "provider_order_id": order["id"], "updated_at": stamp},
                "$unset": {"failure_code": ""}}, session=session)
            if already_paid: return {"alreadyPaid": True, "courseSlug": course["slug"]}
            return {"courseSlug": course["slug"], "courseTitle": course["title"], "amount": intent["amount_paise"],
                "currency": intent["currency"], "orderId": order["id"], "receipt": intent["receipt"],
                "keyId": provider.get_razorpay_settings().key_id, "learnerName": learner["name"], "learnerEmail": learner["email"]}
        return self.db(lambda: self.courses._transaction(persist))

    def verify(self, course_slug, user, payload):
        identifier, stamp = str(uuid4()), now()
        def verify(session):
            require_payment_intents(self.database, session)
            course = self.courses._course(course_slug, session)
            self._user(user["id"], session)
            query = {"course_id": course["_id"], "user_id": user["id"], "provider_order_id": payload["razorpayOrderId"]}
            order = self.database.payment_orders.find_one(query, session=session)
            if order is None: raise HTTPException(404, "Payment order record was not found.")
            if (not re.fullmatch(r"[0-9a-fA-F]{64}", payload["razorpaySignature"])
                    or order["provider"] != "razorpay" or not provider.verify_razorpay_signature(
                    order_id=order["provider_order_id"], payment_id=payload["razorpayPaymentId"], signature=payload["razorpaySignature"])):
                raise HTTPException(400, "Payment verification failed.")
            if order.get("provider_payment_id") not in (None, payload["razorpayPaymentId"]):
                raise HTTPException(409, "This order is already bound to another payment.")
            if order["status"] == "failed": raise HTTPException(409, "This payment order is marked failed.")
            if order["status"] == "paid":
                if order.get("provider_payment_id") != payload["razorpayPaymentId"]:
                    raise HTTPException(409, "The confirmed order has no matching payment identity.")
                # Read-only replay: preserve its identity, timestamps, and current access policy.
                return self.courses._detail(course, user, session)
            lock_course(self.database, course["_id"], session)
            self.database.payment_orders.update_one({"_id": order["_id"]}, {"$set": {
                "status": "paid", "provider_payment_id": payload["razorpayPaymentId"], "verified_at": stamp}}, session=session)
            self.database.enrollments.update_one({"course_id": course["_id"], "user_id": user["id"]}, {
                "$set": {"payment_status": "paid"}, "$setOnInsert": {"_id": identifier, "schema_version": 1,
                    "enrolled_at": stamp, "enrollment_source": "self"}}, upsert=True, session=session)
            return self.courses._detail(course, user, session)
        return self.db(lambda: self.courses._transaction(verify))
