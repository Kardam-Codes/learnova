"""Inspect or restore a justified pending order; never creates a provider order or grants paid access."""
import argparse
import json
import re

from fastapi import HTTPException
from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.config.payments import fetch_razorpay_order
from backend.db.mongo.init_db import assert_development_database
from backend.db.mongo.payment_schema import require_payment_intents
from backend.modules.courses.mongo_payments import MongoPaymentService, validate_provider_order
from backend.modules.courses.mongo_service import MongoCourseService


def reconcile(database, intent_id, provider_order_id, *, apply=False, fetch_order=None):
    assert_development_database(database.name)
    if not re.fullmatch(r"order_[A-Za-z0-9]+", provider_order_id):
        raise ValueError("Supply a valid known provider order ID.")
    courses = MongoCourseService(database)
    def inspect():
        require_payment_intents(database)
        intent = database.payment_checkout_intents.find_one({"_id": intent_id})
        if intent is None: raise HTTPException(404, "Payment checkout intent was not found.")
        return intent
    intent = courses._payment_db(inspect)
    order = (fetch_order or fetch_razorpay_order)(provider_order_id)
    validate_provider_order(order, intent)
    if order["id"] != provider_order_id or intent.get("provider_order_id") not in (None, provider_order_id):
        raise HTTPException(409, "The provider order does not match this checkout intent.")
    result = {"intent_id": intent_id, "provider_order_id": provider_order_id, "receipt": intent["receipt"],
              "provider_binding_verified": True, "applied": False, "paid_access_granted": False}
    if apply:
        response = MongoPaymentService(courses).persist_order(intent_id, order)
        result.update(applied=True, already_authorized=response.get("alreadyPaid", False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--provider-order", required=True)
    parser.add_argument("--apply", action="store_true", help="Persist pending local state after provider binding checks.")
    args = parser.parse_args()
    settings = get_mongo_settings()
    if settings is None: raise SystemExit("Configure MongoDB first.")
    with create_mongo_client(settings) as client:
        print(json.dumps(reconcile(client[settings.database], args.intent, args.provider_order, apply=args.apply), indent=2))


if __name__ == "__main__":
    main()
