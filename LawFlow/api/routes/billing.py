"""Stripe billing and subscription endpoints."""

import stripe
from flask import Blueprint, jsonify, request

from api.config import config
from api.errors import NotFoundError, ValidationError
from api.middleware.auth import get_current_user_id, login_required
from api.models.user import User
from api.services.database import get_db
from api.services.tier_limits import get_tier_status

bp = Blueprint("billing", __name__, url_prefix="/api/billing")


def _stripe_enabled() -> bool:
    return bool(config.STRIPE_SECRET_KEY and config.STRIPE_PRO_PRICE_ID)


def _setup_stripe() -> None:
    if not _stripe_enabled():
        raise ValidationError("Stripe is not configured")
    stripe.api_key = config.STRIPE_SECRET_KEY


@bp.route("/status", methods=["GET"])
@login_required
def billing_status():
    user_id = get_current_user_id()
    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise NotFoundError("User not found")
        return jsonify(get_tier_status(db, user))


@bp.route("/create-checkout", methods=["POST"])
@login_required
def create_checkout():
    _setup_stripe()
    user_id = get_current_user_id()

    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise NotFoundError("User not found")

        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.display_name,
                metadata={"user_id": user.id},
            )
            customer_id = customer["id"]
            user.stripe_customer_id = customer_id
            db.flush()

        checkout = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": config.STRIPE_PRO_PRICE_ID, "quantity": 1}],
            success_url=f"{config.APP_BASE_URL}/pricing?checkout=success",
            cancel_url=f"{config.APP_BASE_URL}/pricing?checkout=cancel",
            allow_promotion_codes=True,
            metadata={"user_id": user.id},
        )
        return jsonify({"url": checkout["url"], "session_id": checkout["id"]})


@bp.route("/create-portal", methods=["POST"])
@login_required
def create_portal():
    _setup_stripe()
    user_id = get_current_user_id()

    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise NotFoundError("User not found")
        if not user.stripe_customer_id:
            raise ValidationError("No billing account exists for this user")

        portal = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{config.APP_BASE_URL}/profile",
        )
        return jsonify({"url": portal["url"]})


@bp.route("/webhook", methods=["POST"])
def webhook():
    _setup_stripe()
    signature = request.headers.get("Stripe-Signature")
    payload = request.data
    if not signature or not config.STRIPE_WEBHOOK_SECRET:
        raise ValidationError("Stripe webhook secret is not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=config.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise ValidationError("Invalid Stripe webhook payload") from exc

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    with get_db() as db:
        if event_type == "checkout.session.completed":
            customer_id = data_object.get("customer")
            subscription_id = data_object.get("subscription")
            if customer_id:
                user = db.query(User).filter_by(stripe_customer_id=customer_id).first()
                if user:
                    user.stripe_subscription_id = subscription_id
                    user.subscription_status = "active"
                    user.tier = "pro"
        elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            customer_id = data_object.get("customer")
            status = data_object.get("status") or "none"
            subscription_id = data_object.get("id")
            if customer_id:
                user = db.query(User).filter_by(stripe_customer_id=customer_id).first()
                if user:
                    user.stripe_subscription_id = subscription_id
                    user.subscription_status = status
                    user.tier = "pro" if status in {"active", "trialing"} else "free"
        elif event_type == "customer.subscription.deleted":
            customer_id = data_object.get("customer")
            if customer_id:
                user = db.query(User).filter_by(stripe_customer_id=customer_id).first()
                if user:
                    user.subscription_status = "canceled"
                    user.tier = "free"

    return jsonify({"received": True})
