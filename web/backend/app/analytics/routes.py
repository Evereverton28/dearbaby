"""
Self-hosted analytics: one endpoint, raw events, aggregates computed at query
time. No third-party script, and the data stays yours.
"""

from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.extensions import db
from app.models import AnalyticsEvent
from app.decorators import permission_required

analytics_bp = Blueprint("analytics", __name__)


def _parse_ua(ua: str):
    """Minimal server-side user-agent parsing; swap in `user-agents` for depth."""
    ua = (ua or "").lower()
    if "ipad" in ua or "tablet" in ua:
        device = "tablet"
    elif "mobi" in ua or "android" in ua or "iphone" in ua:
        device = "mobile"
    else:
        device = "desktop"

    if "edg/" in ua:        browser = "Edge"
    elif "chrome" in ua:    browser = "Chrome"
    elif "safari" in ua:    browser = "Safari"
    elif "firefox" in ua:   browser = "Firefox"
    else:                   browser = "Other"

    if "windows" in ua:                     os_name = "Windows"
    elif "android" in ua:                   os_name = "Android"
    elif "iphone" in ua or "ipad" in ua:    os_name = "iOS"
    elif "mac os" in ua:                    os_name = "macOS"
    elif "linux" in ua:                     os_name = "Linux"
    else:                                   os_name = "Other"

    return device, browser, os_name


@analytics_bp.post("/track")
def track():
    """Public. The frontend fires a pageview per route change, plus funnel
    events: signup_started -> account_created -> first_memory_added -> subscribed."""
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify(error="Event name is required"), 400

    device, browser, os_name = _parse_ua(request.headers.get("User-Agent", ""))

    user_id = None
    try:                                  # attach the user when signed in
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        pass

    db.session.add(AnalyticsEvent(
        visitor_id=data.get("visitor_id"),
        session_id=data.get("session_id"),
        user_id=user_id,
        name=data["name"],
        path=data.get("path"),
        referrer=data.get("referrer"),
        device_type=device, browser=browser, os=os_name,
    ))
    db.session.commit()
    return jsonify(ok=True), 202


@analytics_bp.get("/admin/analytics/summary")
@permission_required("analytics")
def summary():
    """Aggregates computed at query time, never stored as running counters."""
    days = int(request.args.get("days", 30))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = AnalyticsEvent.query.filter(AnalyticsEvent.created_at >= since)

    by_device = dict(
        db.session.query(AnalyticsEvent.device_type, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.created_at >= since)
        .group_by(AnalyticsEvent.device_type).all()
    )
    top_paths = [
        {"path": p, "views": c} for p, c in
        db.session.query(AnalyticsEvent.path, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.created_at >= since, AnalyticsEvent.name == "pageview")
        .group_by(AnalyticsEvent.path)
        .order_by(func.count(AnalyticsEvent.id).desc()).limit(10).all()
    ]
    funnel_steps = ["signup_started", "account_created", "first_memory_added", "subscribed"]
    funnel = [
        {"step": s,
         "count": db.session.query(func.count(func.distinct(AnalyticsEvent.visitor_id)))
                  .filter(AnalyticsEvent.created_at >= since, AnalyticsEvent.name == s).scalar()}
        for s in funnel_steps
    ]

    return jsonify(
        window_days=days,
        total_events=base.count(),
        unique_visitors=db.session.query(func.count(func.distinct(AnalyticsEvent.visitor_id)))
                         .filter(AnalyticsEvent.created_at >= since).scalar(),
        by_device=by_device,
        top_paths=top_paths,
        funnel=funnel,
    ), 200
