"""Subscriptions and payments.

Stripe covers cards, Apple Pay and Google Pay — the latter two are payment
methods riding on the same Stripe session, not separate integrations.

The Stripe call itself is an INTEGRATION POINT (a single, clearly commented
location). The subscription state machine around it is real and tested.
"""
import secrets
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from dearbaby.extensions import db
from dearbaby.models import Subscription, Payment, User
from dearbaby.decorators import login_required, _current_user
from dearbaby.helpers import json_body, active_subscription

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
    db.session.add(sub)
    db.session.commit()
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
                  provider_ref="cs_test_" + secrets.token_hex(8),
                  raw={"plan": plan})
    db.session.add(pay)
    db.session.commit()
    return jsonify(payment_id=pay.id, provider="stripe",
                   checkout_url="https://checkout.stripe.example/" + pay.provider_ref,
                   amount_cents=amount, currency=currency,
                   scaffolded=True), 200


@billing_bp.post("/webhooks/stripe")
def stripe_webhook():
    """
    Stripe calls this when a checkout completes.

    ---- INTEGRATION POINT: verify the Stripe-Signature header ---------
    Use stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    before trusting anything in the body.
    -------------------------------------------------------------------

    Never treat the checkout endpoint's own response as payment. Money is
    only confirmed here.
    """
    body = request.get_json(silent=True) or {}
    event = body.get("type")
    ref = body.get("data", {}).get("object", {}).get("id")
    pay = Payment.query.filter_by(provider_ref=ref, provider="stripe").first()
    if pay is None:
        return jsonify(received=True), 200          # unknown ref: ack and ignore
    if pay.status != "pending":
        return jsonify(received=True), 200          # idempotent: safe to replay

    if event == "checkout.session.completed":
        pay.status = "succeeded"
        _activate(pay, "stripe", (pay.raw or {}).get("plan", "monthly"))
    elif event in ("checkout.session.expired", "payment_intent.payment_failed"):
        pay.status = "failed"
    pay.raw = {**(pay.raw or {}), "event": body}
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
    """Cancels at period end - they keep what they've already paid for."""
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
