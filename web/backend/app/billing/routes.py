"""Subscriptions and payments.

Stripe covers cards, Apple Pay and Google Pay. M-PESA is a separate direct
integration because Safaricom's Daraja API is callback-driven and has no
native recurring billing.

Both provider calls are INTEGRATION POINTS — single, clearly commented
locations. The subscription state machine around them is real and works.
"""
import secrets
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request, current_app
from app.extensions import db
from app.models import Subscription, Payment, User
from app.decorators import login_required, _current_user
from app.helpers import json_body, active_subscription

billing_bp = Blueprint("billing", __name__)

PRICES = {  # amounts in cents of the listed currency
    "monthly": {"KES": 49900, "USD": 399},
    "annual":  {"KES": 449900, "USD": 3499},
}
TRIAL_DAYS = 30


@billing_bp.get("/plans")
def plans():
    return jsonify(trial_days=TRIAL_DAYS, plans=[
        {"key": "monthly", "label": "Monthly", "prices": PRICES["monthly"]},
        {"key": "annual", "label": "Annual", "prices": PRICES["annual"],
         "note": "Two months free"},
    ], premium_features=[
        "Unlimited photo and video backup",
        "Digital scrapbook and printable books",
        "Share albums with family",
        "Export everything, any time",
    ]), 200


@billing_bp.get("/subscription")
@login_required
def my_subscription():
    sub = active_subscription(_current_user().id)
    if sub is None:
        return jsonify(subscription=None, premium=False), 200
    return jsonify(subscription=sub.to_dict(), premium=sub.is_premium()), 200


@billing_bp.post("/subscription/trial")
@login_required
def start_trial():
    """30-day free trial. One per account."""
    user = _current_user()
    if Subscription.query.filter_by(user_id=user.id).first():
        return jsonify(error="You've already used your free trial"), 409
    sub = Subscription(user_id=user.id, plan=json_body().get("plan") or "monthly",
                       status="trialing", provider="none",
                       trial_ends_at=datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS))
    db.session.add(sub); db.session.commit()
    return jsonify(sub.to_dict()), 201


@billing_bp.post("/subscription/checkout")
@login_required
def checkout():
    """
    Card / Apple Pay / Google Pay.

    ---- INTEGRATION POINT: Stripe ------------------------------------
    Replace the stub below with:
        stripe.checkout.Session.create(mode="subscription", ...)
    and return session.url. Apple Pay and Google Pay ride on the same
    Stripe session — they are payment methods, not separate integrations.

    NOTE ON APP STORES: selling this subscription inside the iOS/Android
    apps generally requires Apple/Google in-app purchase (15-30% cut).
    Stripe checkout is for the WEB. Decide this before wiring the mobile
    paywall.
    -------------------------------------------------------------------
    """
    user = _current_user()
    d = json_body()
    plan = d.get("plan")
    if plan not in PRICES:
        return jsonify(error="Choose a monthly or annual plan"), 400
    currency = d.get("currency", "KES")
    amount = PRICES[plan].get(currency)
    if amount is None:
        return jsonify(error="Unsupported currency"), 400

    pay = Payment(user_id=user.id, provider="stripe", amount_cents=amount,
                  currency=currency, status="pending",
                  provider_ref=f"cs_test_{secrets.token_hex(8)}")
    db.session.add(pay); db.session.commit()
    return jsonify(payment_id=pay.id, provider="stripe",
                   checkout_url=f"https://checkout.stripe.example/{pay.provider_ref}",
                   amount_cents=amount, currency=currency,
                   scaffolded=True), 200


@billing_bp.post("/subscription/mpesa/stk-push")
@login_required
def mpesa_stk_push():
    """
    M-PESA STK Push. The user gets a PIN prompt on their phone; Safaricom
    then calls our /webhooks/mpesa callback with the result.

    ---- INTEGRATION POINT: Safaricom Daraja --------------------------
    POST https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest
    with BusinessShortCode, a base64 Password (shortcode+passkey+timestamp),
    Amount, PartyA (phone), CallbackURL, AccountReference.
    Requires: Consumer Key/Secret, Shortcode, Passkey.
    -------------------------------------------------------------------

    NEVER treat this endpoint's own 200 as payment. Money is only confirmed
    by the callback below.
    """
    user = _current_user()
    d = json_body()
    phone = (d.get("phone") or "").strip().replace("+", "")
    if not phone.startswith("254") or len(phone) != 12:
        return jsonify(error="Enter a Safaricom number as 2547XXXXXXXX"), 400
    plan = d.get("plan")
    if plan not in PRICES:
        return jsonify(error="Choose a monthly or annual plan"), 400

    pay = Payment(user_id=user.id, provider="mpesa", amount_cents=PRICES[plan]["KES"],
                  currency="KES", status="pending",
                  provider_ref=f"ws_CO_{secrets.token_hex(8)}",
                  raw={"phone": phone, "plan": plan})
    db.session.add(pay); db.session.commit()
    return jsonify(payment_id=pay.id, checkout_request_id=pay.provider_ref,
                   status="pending",
                   message="Check your phone for the M-PESA prompt",
                   scaffolded=True), 202


@billing_bp.post("/webhooks/mpesa")
def mpesa_callback():
    """
    Safaricom calls this. No auth header — validate by source IP allowlist
    and by matching CheckoutRequestID against a payment we initiated.
    """
    body = request.get_json(silent=True) or {}
    stk = body.get("Body", {}).get("stkCallback", {})
    ref = stk.get("CheckoutRequestID")
    code = stk.get("ResultCode")
    pay = Payment.query.filter_by(provider_ref=ref, provider="mpesa").first()
    if pay is None:
        return jsonify(ResultCode=0, ResultDesc="Unknown reference, ignored"), 200
    if pay.status != "pending":
        return jsonify(ResultCode=0, ResultDesc="Already processed"), 200  # idempotent

    if code == 0:
        pay.status = "succeeded"
        _activate(pay, "mpesa", (pay.raw or {}).get("plan", "monthly"))
    else:
        pay.status = "failed"
    pay.raw = {**(pay.raw or {}), "callback": body}
    db.session.commit()
    return jsonify(ResultCode=0, ResultDesc="Accepted"), 200


@billing_bp.post("/webhooks/stripe")
def stripe_webhook():
    """---- INTEGRATION POINT: verify the Stripe-Signature header ----"""
    body = request.get_json(silent=True) or {}
    event = body.get("type")
    ref = body.get("data", {}).get("object", {}).get("id")
    pay = Payment.query.filter_by(provider_ref=ref, provider="stripe").first()
    if pay is None:
        return jsonify(received=True), 200
    if event == "checkout.session.completed" and pay.status == "pending":
        pay.status = "succeeded"
        _activate(pay, "stripe", body.get("data", {}).get("object", {}).get("plan", "monthly"))
    db.session.commit()
    return jsonify(received=True), 200


def _activate(payment, provider, plan):
    """Move the user's subscription to active for one billing period."""
    days = 365 if plan == "annual" else 30
    sub = active_subscription(payment.user_id)
    if sub is None:
        sub = Subscription(user_id=payment.user_id, plan=plan)
        db.session.add(sub)
    sub.plan = plan
    sub.status = "active"
    sub.provider = provider
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=days)
    sub.cancel_at_period_end = False
    db.session.flush()
    payment.subscription_id = sub.id


@billing_bp.post("/subscription/cancel")
@login_required
def cancel():
    """Cancels at period end — they keep what they paid for."""
    sub = active_subscription(_current_user().id)
    if sub is None or sub.status not in ("active", "trialing"):
        return jsonify(error="No active subscription"), 404
    sub.cancel_at_period_end = True
    db.session.commit()
    return jsonify(sub.to_dict()), 200


@billing_bp.get("/payments")
@login_required
def payment_history():
    items = (Payment.alive().filter_by(user_id=_current_user().id)
             .order_by(Payment.created_at.desc()).limit(50).all())
    return jsonify(payments=[p.to_dict() for p in items]), 200
