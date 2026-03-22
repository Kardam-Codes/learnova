"""
File: payments.py
Owner: BOTH CAN ADD
Created: 2026-03-22
Project: Learnova (eLearning Platform)
Purpose: Provide Razorpay configuration and low-level payment helpers.
What it is: A small standard-library-only integration layer for order creation and signature verification.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from urllib import error, request

from fastapi import HTTPException, status


RAZORPAY_ORDER_URL = "https://api.razorpay.com/v1/orders"


@dataclass(frozen=True)
class RazorpaySettings:
    key_id: str
    key_secret: str
    currency: str


def get_razorpay_settings() -> RazorpaySettings:
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    currency = os.getenv("RAZORPAY_CURRENCY", "INR").strip() or "INR"

    return RazorpaySettings(
        key_id=key_id,
        key_secret=key_secret,
        currency=currency,
    )


def ensure_razorpay_configured() -> RazorpaySettings:
    settings = get_razorpay_settings()
    if not settings.key_id or not settings.key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured yet.",
        )
    return settings


def create_razorpay_order(*, amount_paise: int, receipt: str, notes: dict[str, str] | None = None) -> dict:
    settings = ensure_razorpay_configured()

    payload = json.dumps(
        {
            "amount": amount_paise,
            "currency": settings.currency,
            "receipt": receipt,
            "notes": notes or {},
        }
    ).encode("utf-8")
    basic_token = base64.b64encode(f"{settings.key_id}:{settings.key_secret}".encode("utf-8")).decode("utf-8")

    http_request = request.Request(
        RAZORPAY_ORDER_URL,
        data=payload,
        headers={
            "Authorization": f"Basic {basic_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Razorpay order creation failed. {details}".strip(),
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Razorpay from the backend.",
        ) from exc


def verify_razorpay_signature(*, order_id: str, payment_id: str, signature: str) -> bool:
    settings = ensure_razorpay_configured()
    signing_payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected_signature = hmac.new(
        settings.key_secret.encode("utf-8"),
        signing_payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
