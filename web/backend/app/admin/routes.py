"""
Admin area. Every route is gated server-side by permission_required(...).
Account management is additionally narrowed by the HIERARCHY map.
"""

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User
from app.decorators import permission_required, assert_can_manage, _current_user
from app.roles import manageable_roles, PERMISSIONS, HIERARCHY

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/users")
@permission_required("users")
def list_users():
    """Listing is broad; ACTING on an account is what the hierarchy narrows."""
    role_filter = request.args.get("role")
    q = User.query
    if role_filter:
        q = q.filter_by(role=role_filter)
    users = q.order_by(User.created_at.desc()).limit(200).all()
    actor = _current_user()
    return jsonify(
        users=[u.to_dict() for u in users],
        assignable_roles=manageable_roles(actor.role),  # drives the role dropdown
    ), 200


@admin_bp.post("/users")
@permission_required("users")
def create_user():
    actor = _current_user()
    data = request.get_json(silent=True) or {}
    role = data.get("role")

    # The hierarchy is the authority on which roles this actor may assign.
    if role not in manageable_roles(actor.role):
        return jsonify(error="Outside your management scope"), 403

    email = (data.get("email") or "").strip().lower()
    if not email or not data.get("password") or not data.get("display_name"):
        return jsonify(error="Email, password and name are required"), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="That email is already registered"), 409

    user = User(email=email, display_name=data["display_name"].strip(), role=role)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@admin_bp.patch("/users/<user_id>")
@permission_required("users")
def update_user(user_id):
    actor = _current_user()
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify(error="User not found"), 404

    denied = assert_can_manage(actor, target)
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    if "display_name" in data:
        target.display_name = data["display_name"].strip()
    if "role" in data and data["role"] != target.role:
        if data["role"] not in manageable_roles(actor.role):
            return jsonify(error="Outside your management scope"), 403
        target.role = data["role"]
    db.session.commit()
    return jsonify(target.to_dict()), 200


@admin_bp.post("/users/<user_id>/deactivate")
@permission_required("users")
def deactivate_user(user_id):
    """
    Retains data and history; blocks sign-in AND kills any live session
    immediately, because is_active is checked in the token-validation
    blocklist callback (see app/__init__.py), not just in route guards.
    """
    actor = _current_user()
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify(error="User not found"), 404

    denied = assert_can_manage(actor, target)
    if denied:
        return denied

    target.is_active = False
    db.session.commit()
    return jsonify(target.to_dict()), 200


@admin_bp.post("/users/<user_id>/reactivate")
@permission_required("users")
def reactivate_user(user_id):
    actor = _current_user()
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify(error="User not found"), 404
    denied = assert_can_manage(actor, target)
    if denied:
        return denied
    target.is_active = True
    db.session.commit()
    return jsonify(target.to_dict()), 200


# --- other admin capabilities, each gated by its own permission ---------
@admin_bp.get("/moderation/reports")
@permission_required("moderation")
def moderation_queue():
    # Moderators reach this; parents get 403. Wire to the reports table next.
    return jsonify(reports=[], note="Moderation queue — wire to reports table"), 200


@admin_bp.get("/subscriptions")
@permission_required("subscriptions")
def subscriptions():
    return jsonify(subscriptions=[], note="Wire to subscriptions table"), 200


@admin_bp.get("/settings")
@permission_required("*")
def system_settings():
    """System settings are super_admin only — no other role holds '*'."""
    return jsonify(settings={}, note="Super-admin only"), 200


@admin_bp.get("/roles")
@permission_required("users")
def role_reference():
    """Exposes the maps so the client mirror can be verified against the server."""
    return jsonify(
        permissions={r: sorted(p) for r, p in PERMISSIONS.items()},
        hierarchy={r: sorted(t) for r, t in HIERARCHY.items()},
    ), 200


# =====================================================================
# Moderation queue, announcements, and admin analytics
# =====================================================================
from datetime import datetime, timezone
from app.models import (Report, Post, Comment, ModerationAction, Announcement,
                        Subscription, Payment, Child, Milestone)
from app.helpers import json_body, paginate


@admin_bp.get("/reports")
@permission_required("moderation")
def list_reports():
    status = request.args.get("status", "open")
    q = Report.alive().filter_by(status=status).order_by(Report.created_at.desc())
    items, meta = paginate(q, default=30)
    reporters = {u.id: u for u in User.query.filter(
        User.id.in_([r.reporter_id for r in items] or ["__none__"])).all()}
    out = []
    for r in items:
        snippet = None
        if r.entity_type == "post":
            p = db.session.get(Post, r.entity_id)
            snippet = (p.body[:240] if p else None)
        elif r.entity_type == "comment":
            c = db.session.get(Comment, r.entity_id)
            snippet = (c.body[:240] if c else None)
        out.append(r.to_dict(snippet, reporters.get(r.reporter_id)))
    return jsonify(reports=out, **meta), 200


@admin_bp.post("/reports/<rid>/action")
@permission_required("moderation")
def act_on_report(rid):
    """hide | remove | dismiss. Every action is written to an audit log."""
    actor = _current_user()
    r = Report.alive().filter_by(id=rid).first()
    if r is None:
        return jsonify(error="Not found"), 404
    d = json_body()
    action = d.get("action")
    if action not in ("hide", "remove", "dismiss"):
        return jsonify(error="action must be hide, remove or dismiss"), 400

    if action in ("hide", "remove"):
        model = Post if r.entity_type == "post" else Comment
        target = db.session.get(model, r.entity_id)
        if target is not None:
            target.status = "hidden" if action == "hide" else "removed"
        r.status = "actioned"
    else:
        r.status = "dismissed"

    r.handled_by = actor.id
    db.session.add(ModerationAction(moderator_id=actor.id, entity_type=r.entity_type,
                                    entity_id=r.entity_id, action=action,
                                    reason=d.get("reason")))
    db.session.commit()
    return jsonify(r.to_dict()), 200


@admin_bp.get("/moderation/log")
@permission_required("moderation")
def moderation_log():
    rows = (ModerationAction.query.order_by(ModerationAction.created_at.desc())
            .limit(100).all())
    mods = {u.id: u for u in User.query.filter(
        User.id.in_([r.moderator_id for r in rows] or ["__none__"])).all()}
    return jsonify(actions=[{
        "id": r.id, "action": r.action, "entity_type": r.entity_type,
        "entity_id": r.entity_id, "reason": r.reason,
        "moderator": mods[r.moderator_id].public() if r.moderator_id in mods else None,
        "created_at": r.created_at.isoformat()} for r in rows]), 200


@admin_bp.get("/announcements")
@permission_required("announcements")
def list_announcements():
    rows = Announcement.alive().order_by(Announcement.created_at.desc()).limit(50).all()
    return jsonify(announcements=[a.to_dict() for a in rows]), 200


@admin_bp.post("/announcements")
@permission_required("announcements")
def create_announcement():
    actor = _current_user()
    d = json_body()
    if not d.get("title") or not d.get("body"):
        return jsonify(error="Title and message are required"), 400
    a = Announcement(author_id=actor.id, title=d["title"].strip(), body=d["body"].strip(),
                     audience=d.get("audience", "all"))
    if d.get("publish"):
        a.published_at = datetime.now(timezone.utc)
        # ---- INTEGRATION POINT: fan-out ---------------------------------
        # Queue a job to create a Notification per targeted user and send a
        # push. Writing one row per user inline would block the request.
    db.session.add(a); db.session.commit()
    return jsonify(a.to_dict()), 201


@admin_bp.get("/overview")
@permission_required("analytics")
def overview():
    """Dashboard headline numbers."""
    subs = Subscription.query.all()
    return jsonify(
        users={"total": User.query.count(),
               "active": User.query.filter_by(is_active=True).count(),
               "parents": User.query.filter_by(role="parent").count()},
        content={"children": Child.alive().count(),
                 "milestones": Milestone.alive().count(),
                 "posts": Post.alive().filter_by(status="visible").count()},
        moderation={"open_reports": Report.alive().filter_by(status="open").count()},
        subscriptions={"trialing": sum(1 for s in subs if s.status == "trialing"),
                       "active": sum(1 for s in subs if s.status == "active"),
                       "canceled": sum(1 for s in subs if s.status == "canceled")},
        revenue_cents=sum(p.amount_cents or 0 for p in
                          Payment.query.filter_by(status="succeeded").all()),
    ), 200


@admin_bp.get("/subscriptions/list")
@permission_required("subscriptions")
def subscriptions_list():
    q = Subscription.query.order_by(Subscription.created_at.desc())
    items, meta = paginate(q, default=50)
    users = {u.id: u for u in User.query.filter(
        User.id.in_([s.user_id for s in items] or ["__none__"])).all()}
    return jsonify(subscriptions=[{**s.to_dict(),
                                   "user": users[s.user_id].public()
                                   if s.user_id in users else None}
                                  for s in items], **meta), 200
