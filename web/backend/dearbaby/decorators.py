"""
Server-side authorization. Every protected route passes through here.

Two rules from the architecture brief that are easy to get wrong:

1. The `role` claim inside the JWT is a CONVENIENCE, NOT THE AUTHORITY.
   Each guard re-reads the role from the database on every request, so a
   demotion takes effect immediately instead of when the token expires.

2. Deactivation is enforced at the TOKEN-VALIDATION LAYER (the blocklist
   callback in app/__init__.py), not only in these route guards. A guard-only
   check would leave every plain @jwt_required() route accepting a deactivated
   user's already-issued token until it expired.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from dearbaby.extensions import db
from dearbaby.models import User
from dearbaby.roles import has_permission, can_manage


def _current_user():
    """Resolve the token subject to a live database row."""
    return db.session.get(User, get_jwt_identity())


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = _current_user()
        if user is None:
            return jsonify(error="Account not found"), 401
        return fn(*args, **kwargs)
    return wrapper


def permission_required(capability):
    """
    Gate a route on a capability. Re-reads the role from the DB per request.

        @admin_bp.get("/subscriptions")
        @permission_required("subscriptions")
        def list_subscriptions(): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = _current_user()
            if user is None:
                return jsonify(error="Account not found"), 401
            if not user.is_active:
                return jsonify(error="Account is deactivated"), 403
            if not has_permission(user.role, capability):
                return jsonify(error="Insufficient permissions"), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def assert_can_manage(actor: User, target: User):
    """
    Hierarchy check for account-management actions. Returns an (error, status)
    tuple, or None when the action is allowed.

    Enforces the two protections worth copying:
      - nobody may act on their own account (no self-lockout, no self-deletion)
      - the highest role is not manageable through the panel (HIERARCHY simply
        never lists super_admin as a manageable target)
    """
    if actor.id == target.id:
        return jsonify(error="You cannot modify your own account here"), 400
    if not can_manage(actor.role, target.role):
        return jsonify(error="Outside your management scope"), 403
    return None
