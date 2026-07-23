"""Shared request helpers: ownership checks, pagination, premium gating."""
from datetime import datetime, date
from functools import wraps
from flask import request, jsonify
from dearbaby.extensions import db
from dearbaby.models import Child, ChildMember, Subscription, Media, MediaLink


def json_body():
    return request.get_json(silent=True) or {}


def parse_date(v):
    if not v:
        return None
    try:
        return date.fromisoformat(v[:10])
    except ValueError:
        return None


def parse_dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_child_or_403(child_id, user, need_edit=False):
    """
    Resolve a child the user is allowed to touch.
    Returns (child, None) or (None, (response, status)).

    A child is reachable by its owner, or by an invited co-parent via
    ChildMember. Everything under /api/children/<id>/... goes through here,
    so no feature route has to re-implement the ownership rule.
    """
    child = Child.query.filter_by(id=child_id, deleted_at=None).first()
    if child is None:
        return None, (jsonify(error="Not found"), 404)
    if child.owner_id == user.id:
        return child, None
    member = ChildMember.query.filter_by(child_id=child_id, user_id=user.id).first()
    if member is None:
        return None, (jsonify(error="Not found"), 404)   # don't leak existence
    if need_edit and not member.can_edit:
        return None, (jsonify(error="You have view-only access"), 403)
    return child, None


def paginate(query, default=20, max_limit=100):
    limit = min(int(request.args.get("limit", default)), max_limit)
    offset = int(request.args.get("offset", 0))
    total = query.count()
    items = query.limit(limit).offset(offset).all()
    return items, {"total": total, "limit": limit, "offset": offset,
                   "has_more": offset + len(items) < total}


def active_subscription(user_id):
    return (Subscription.query.filter_by(user_id=user_id)
            .order_by(Subscription.created_at.desc()).first())


def is_premium(user_id):
    sub = active_subscription(user_id)
    return bool(sub and sub.is_premium())


def premium_required(fn):
    """Gate a premium feature. Returns 402 so the client can show the paywall."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from dearbaby.decorators import _current_user
        user = _current_user()
        if not is_premium(user.id):
            return jsonify(error="This is a premium feature",
                           code="upgrade_required"), 402
        return fn(*args, **kwargs)
    return wrapper


def attach_media(entity_type, entity_id, media_ids):
    for i, mid in enumerate(media_ids or []):
        if not MediaLink.query.filter_by(media_id=mid, entity_type=entity_type,
                                         entity_id=entity_id).first():
            db.session.add(MediaLink(media_id=mid, entity_type=entity_type,
                                     entity_id=entity_id, position=i))


def media_for(entity_type, entity_id):
    links = MediaLink.query.filter_by(entity_type=entity_type,
                                      entity_id=entity_id).order_by(MediaLink.position).all()
    if not links:
        return []
    ids = [l.media_id for l in links]
    items = Media.query.filter(Media.id.in_(ids), Media.deleted_at.is_(None)).all()
    order = {mid: i for i, mid in enumerate(ids)}
    return [m.to_dict() for m in sorted(items, key=lambda m: order.get(m.id, 0))]
