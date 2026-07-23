"""
Authentication. ONE login endpoint for everyone — parents, moderators, admins.
There is no separate "admin password check". The role on the account decides
where the client sends the user and what the server permits.

TWO SIGNUP DOORS, on purpose:
  /register        public   -> ALWAYS creates a parent. Role in the body is ignored.
  /admin-register  gated    -> requires the invite code; the only public path
                              that can mint a privileged account.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)
from app.extensions import db
from app.models import User
from app.decorators import login_required, _current_user
from app.roles import (
    DEFAULT_PUBLIC_ROLE, LANDING, PERMISSIONS, ALL_ROLES,
    SUPER_ADMIN, ADMIN, MODERATOR,
)

auth_bp = Blueprint("auth", __name__)


def _issue(user):
    """Role travels in the token as a convenience claim; guards re-verify from DB."""
    claims = {"role": user.role}
    return {
        "access_token": create_access_token(identity=user.id, additional_claims=claims),
        "refresh_token": create_refresh_token(identity=user.id, additional_claims=claims),
        "user": user.to_dict(),
        "landing": LANDING.get(user.role, "/app"),
        "permissions": sorted(PERMISSIONS.get(user.role, set())),  # UX only
    }


@auth_bp.post("/register")
def register():
    """PUBLIC DOOR. The role is hardcoded server-side and never read from the
    payload — otherwise anyone could POST {"role": "super_admin"}."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip()

    if not email or not password or not display_name:
        return jsonify(error="Email, password and name are required"), 400
    if len(password) < 8:
        return jsonify(error="Password must be at least 8 characters"), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="That email is already registered"), 409

    user = User(email=email, display_name=display_name, role=DEFAULT_PUBLIC_ROLE)
    #                                                   ^^^^^^^^^^^^^^^^^^^
    # Hardcoded. data.get("role") is deliberately never consulted here.
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(_issue(user)), 201


@auth_bp.post("/admin-register")
def admin_register():
    """GATED DOOR. Requires the shared invite code. Cannot mint a super_admin —
    the highest role comes only from the seed script."""
    data = request.get_json(silent=True) or {}
    if data.get("invite_code") != current_app.config["ADMIN_INVITE_CODE"]:
        return jsonify(error="Invalid invite code"), 403

    role = data.get("role") or MODERATOR
    if role not in (ADMIN, MODERATOR):
        return jsonify(error="That role cannot be created here"), 403

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip()
    if not email or not password or not display_name:
        return jsonify(error="Email, password and name are required"), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="That email is already registered"), 409

    user = User(email=email, display_name=display_name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(_issue(user)), 201


@auth_bp.post("/login")
def login():
    """One login for everyone. The role decides the destination, not the door."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(data.get("password") or ""):
        # Same message either way — don't leak which emails exist.
        return jsonify(error="Incorrect email or password"), 401
    if not user.is_active:
        return jsonify(error="This account has been deactivated"), 403

    return jsonify(_issue(user)), 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user = db.session.get(User, get_jwt_identity())
    if user is None or not user.is_active:
        return jsonify(error="Session revoked"), 401
    return jsonify(_issue(user)), 200


@auth_bp.get("/me")
@login_required
def me():
    user = _current_user()
    return jsonify(
        user=user.to_dict(),
        permissions=sorted(PERMISSIONS.get(user.role, set())),
        landing=LANDING.get(user.role, "/app"),
    ), 200
