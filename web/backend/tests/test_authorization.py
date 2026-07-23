"""
Authorization matrix: every role against every protected route, asserting the
expected status code — plus the bypass attempts that produce real bugs.

Run:  cd web/backend && python -m pytest tests/ -v
"""

import pytest
from dearbaby import create_app
from dearbaby.config import TestConfig
from dearbaby.extensions import db
from dearbaby.models import User
from dearbaby.roles import PARENT, MODERATOR, ADMIN, SUPER_ADMIN

PASSWORD = "correct-horse-battery"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
        for role in (PARENT, MODERATOR, ADMIN, SUPER_ADMIN):
            u = User(email=f"{role}@dearbaby.test", display_name=role.title(), role=role)
            u.set_password(PASSWORD)
            db.session.add(u)
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def token_for(client, role):
    r = client.post("/api/auth/login",
                    json={"email": f"{role}@dearbaby.test", "password": PASSWORD})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["access_token"]


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# =====================================================================
# 1. THE MATRIX — every role against every protected route
# =====================================================================
MATRIX = [
    # (route, method, {role: expected_status})
    ("/api/admin/users", "get", {
        PARENT: 403, MODERATOR: 403, ADMIN: 200, SUPER_ADMIN: 200}),
    ("/api/admin/moderation/reports", "get", {
        PARENT: 403, MODERATOR: 200, ADMIN: 200, SUPER_ADMIN: 200}),
    ("/api/admin/subscriptions", "get", {
        PARENT: 403, MODERATOR: 403, ADMIN: 200, SUPER_ADMIN: 200}),
    ("/api/admin/analytics/summary", "get", {
        PARENT: 403, MODERATOR: 403, ADMIN: 200, SUPER_ADMIN: 200}),
    # system settings require "*" — only super_admin holds it
    ("/api/admin/settings", "get", {
        PARENT: 403, MODERATOR: 403, ADMIN: 403, SUPER_ADMIN: 200}),
]


@pytest.mark.parametrize("route,method,expected", MATRIX)
def test_authorization_matrix(client, route, method, expected):
    for role, status in expected.items():
        tok = token_for(client, role)
        resp = getattr(client, method)(route, headers=auth(tok))
        assert resp.status_code == status, (
            f"{role} {method.upper()} {route} -> {resp.status_code}, expected {status}")


def test_protected_routes_reject_missing_token(client):
    for route, method, _ in MATRIX:
        resp = getattr(client, method)(route)
        assert resp.status_code == 401, f"{route} allowed an unauthenticated call"


# =====================================================================
# 2. BYPASS: privilege escalation through the public signup door
# =====================================================================
@pytest.mark.parametrize("attempted_role", [SUPER_ADMIN, ADMIN, MODERATOR])
def test_public_signup_ignores_role_in_payload(client, attempted_role):
    r = client.post("/api/auth/register", json={
        "email": f"sneaky-{attempted_role}@x.com",
        "password": PASSWORD,
        "display_name": "Sneaky",
        "role": attempted_role,          # <- the attack
    })
    assert r.status_code == 201
    assert r.get_json()["user"]["role"] == PARENT


def test_admin_register_requires_invite_code(client):
    r = client.post("/api/auth/admin-register", json={
        "email": "no-code@x.com", "password": PASSWORD,
        "display_name": "No Code", "role": MODERATOR})
    assert r.status_code == 403

    r = client.post("/api/auth/admin-register", json={
        "email": "with-code@x.com", "password": PASSWORD,
        "display_name": "With Code", "role": MODERATOR,
        "invite_code": TestConfig.ADMIN_INVITE_CODE})
    assert r.status_code == 201
    assert r.get_json()["user"]["role"] == MODERATOR


def test_admin_register_cannot_mint_super_admin(client):
    r = client.post("/api/auth/admin-register", json={
        "email": "escalate@x.com", "password": PASSWORD,
        "display_name": "Escalate", "role": SUPER_ADMIN,
        "invite_code": TestConfig.ADMIN_INVITE_CODE})
    assert r.status_code == 403


# =====================================================================
# 3. HIERARCHY — admin-over-admin
# =====================================================================
def test_admin_cannot_manage_another_admin(app, client):
    with app.app_context():
        other = User.query.filter_by(role=ADMIN).first().id
        sup = User.query.filter_by(role=SUPER_ADMIN).first().id
        mod = User.query.filter_by(role=MODERATOR).first().id

    admin_tok = token_for(client, ADMIN)
    # its own account -> 400 (no self-lockout)
    assert client.post(f"/api/admin/users/{other}/deactivate",
                       headers=auth(admin_tok)).status_code == 400
    # a super_admin -> 403 (highest role not manageable through the panel)
    assert client.post(f"/api/admin/users/{sup}/deactivate",
                       headers=auth(admin_tok)).status_code == 403
    # a moderator -> allowed
    assert client.post(f"/api/admin/users/{mod}/deactivate",
                       headers=auth(admin_tok)).status_code == 200


def test_admin_cannot_assign_role_above_itself(client):
    admin_tok = token_for(client, ADMIN)
    r = client.post("/api/admin/users", headers=auth(admin_tok), json={
        "email": "new-super@x.com", "password": PASSWORD,
        "display_name": "New Super", "role": SUPER_ADMIN})
    assert r.status_code == 403


def test_super_admin_can_manage_admins(app, client):
    with app.app_context():
        admin_id = User.query.filter_by(role=ADMIN).first().id
    sup_tok = token_for(client, SUPER_ADMIN)
    assert client.post(f"/api/admin/users/{admin_id}/deactivate",
                       headers=auth(sup_tok)).status_code == 200


# =====================================================================
# 4. BYPASS: the already-issued token after deactivation
#    (the bug that only surfaces if you test this path)
# =====================================================================
def test_deactivation_revokes_live_session_immediately(app, client):
    mod_tok = token_for(client, MODERATOR)
    # token works right now
    assert client.get("/api/auth/me", headers=auth(mod_tok)).status_code == 200

    with app.app_context():
        mod_id = User.query.filter_by(role=MODERATOR).first().id
    sup_tok = token_for(client, SUPER_ADMIN)
    assert client.post(f"/api/admin/users/{mod_id}/deactivate",
                       headers=auth(sup_tok)).status_code == 200

    # SAME token, not re-issued: must now be rejected at token validation,
    # on a plain @login_required route, not only on admin guards.
    assert client.get("/api/auth/me", headers=auth(mod_tok)).status_code == 401
    assert client.get("/api/admin/moderation/reports",
                      headers=auth(mod_tok)).status_code == 401


def test_deactivated_user_cannot_log_in(app, client):
    with app.app_context():
        mod_id = User.query.filter_by(role=MODERATOR).first().id
    sup_tok = token_for(client, SUPER_ADMIN)
    client.post(f"/api/admin/users/{mod_id}/deactivate", headers=auth(sup_tok))
    r = client.post("/api/auth/login",
                    json={"email": f"{MODERATOR}@dearbaby.test", "password": PASSWORD})
    assert r.status_code == 403


# =====================================================================
# 5. Role changes take effect immediately (token claim is not the authority)
# =====================================================================
def test_demotion_takes_effect_without_reissuing_token(app, client):
    admin_tok = token_for(client, ADMIN)
    assert client.get("/api/admin/subscriptions",
                      headers=auth(admin_tok)).status_code == 200

    with app.app_context():
        u = User.query.filter_by(role=ADMIN).first()
        u.role = MODERATOR          # demoted in the database only
        db.session.commit()

    # The token still CLAIMS admin. The guard re-reads the DB, so: 403.
    assert client.get("/api/admin/subscriptions",
                      headers=auth(admin_tok)).status_code == 403


def test_login_returns_role_based_landing(client):
    assert client.post("/api/auth/login", json={
        "email": f"{PARENT}@dearbaby.test", "password": PASSWORD}
    ).get_json()["landing"] == "/app"
    assert client.post("/api/auth/login", json={
        "email": f"{MODERATOR}@dearbaby.test", "password": PASSWORD}
    ).get_json()["landing"] == "/admin/moderation"
