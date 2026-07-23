"""Feature tests: ownership isolation, premium gating, and the M-PESA
callback contract. These are the paths where a bug costs real trust."""
import pytest
from datetime import date, timedelta
from dearbaby import create_app
from dearbaby.config import TestConfig
from dearbaby.extensions import db
from dearbaby.models import User, Child, PregnancyWeek, Recipe, Subscription
from dearbaby.roles import PARENT

PW = "correct-horse-battery"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.drop_all(); db.create_all()
        for name in ("amara", "joy", "stranger"):
            u = User(email=f"{name}@t.test", display_name=name.title(), role=PARENT)
            u.set_password(PW)
            db.session.add(u)
        db.session.add(PregnancyWeek(week=24, size_label="a cantaloupe", length_cm=30,
                                     weight_g=600, summary="s", tip="t"))
        db.session.add(Recipe(title="Sweet potato puree", category="puree",
                              min_age_months=6, ingredients=[], steps=[]))
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def tok(client, name):
    r = client.post("/api/auth/login", json={"email": f"{name}@t.test", "password": PW})
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def make_child(client, hdr):
    return client.post("/api/children", headers=hdr, json={
        "name": "Baby", "due_date": (date.today() + timedelta(weeks=16)).isoformat(),
    }).get_json()


# ------------------------------------------------------------------
# Ownership isolation: one family's memories must never leak to another
# ------------------------------------------------------------------
def test_stranger_cannot_read_another_familys_child(client):
    amara, stranger = tok(client, "amara"), tok(client, "stranger")
    child = make_child(client, amara)
    r = client.get(f"/api/children/{child['id']}", headers=stranger)
    # 404 not 403 — don't confirm the record even exists
    assert r.status_code == 404


def test_stranger_cannot_write_to_another_familys_journal(client):
    amara, stranger = tok(client, "amara"), tok(client, "stranger")
    child = make_child(client, amara)
    r = client.post(f"/api/pregnancy/children/{child['id']}/journal",
                    headers=stranger, json={"body": "intruding"})
    assert r.status_code == 404


def test_invited_coparent_can_read_but_view_only_cannot_write(app, client):
    amara, joy = tok(client, "amara"), tok(client, "joy")
    child = make_child(client, amara)

    # invite Joy with view-only access
    r = client.post(f"/api/children/{child['id']}/members", headers=amara,
                    json={"email": "joy@t.test", "can_edit": False})
    assert r.status_code == 201

    assert client.get(f"/api/children/{child['id']}", headers=joy).status_code == 200
    r = client.post(f"/api/pregnancy/children/{child['id']}/journal",
                    headers=joy, json={"body": "hello"})
    assert r.status_code == 403          # view-only, not invisible

    # promote to editor
    client.delete(f"/api/children/{child['id']}/members/"
                  + client.get("/api/auth/me", headers=joy).get_json()["user"]["id"],
                  headers=amara)
    client.post(f"/api/children/{child['id']}/members", headers=amara,
                json={"email": "joy@t.test", "can_edit": True})
    assert client.post(f"/api/pregnancy/children/{child['id']}/journal",
                       headers=joy, json={"body": "hello"}).status_code == 201


def test_only_owner_can_delete_or_invite(client):
    amara, joy = tok(client, "amara"), tok(client, "joy")
    child = make_child(client, amara)
    client.post(f"/api/children/{child['id']}/members", headers=amara,
                json={"email": "joy@t.test", "can_edit": True})
    # an editor is not an owner
    assert client.delete(f"/api/children/{child['id']}", headers=joy).status_code == 403
    assert client.post(f"/api/children/{child['id']}/members", headers=joy,
                       json={"email": "stranger@t.test"}).status_code == 403


# ------------------------------------------------------------------
# Premium gating returns 402 so the client can show the paywall
# ------------------------------------------------------------------
def test_print_book_requires_premium(app, client):
    amara = tok(client, "amara")
    child = make_child(client, amara)
    r = client.post(f"/api/children/{child['id']}/print-books".replace(
        "/api/children", "/api/memories/children"), headers=amara, json={"title": "Book"})
    assert r.status_code == 402
    assert r.get_json()["code"] == "upgrade_required"

    client.post("/api/billing/subscription/trial", headers=amara, json={"plan": "monthly"})
    r = client.post(f"/api/memories/children/{child['id']}/print-books",
                    headers=amara, json={"title": "Book"})
    assert r.status_code == 201


def test_trial_can_only_be_claimed_once(client):
    amara = tok(client, "amara")
    assert client.post("/api/billing/subscription/trial", headers=amara,
                       json={"plan": "monthly"}).status_code == 201
    assert client.post("/api/billing/subscription/trial", headers=amara,
                       json={"plan": "annual"}).status_code == 409


# ------------------------------------------------------------------
# Payments: money is only real once the webhook confirms it
# ------------------------------------------------------------------
def test_checkout_does_not_grant_premium_on_its_own(client):
    amara = tok(client, "amara")
    r = client.post("/api/billing/subscription/checkout", headers=amara,
                    json={"plan": "annual", "currency": "KES"})
    assert r.status_code == 200
    assert client.get("/api/billing/subscription",
                      headers=amara).get_json()["premium"] is False


def test_successful_webhook_activates_subscription(client):
    amara = tok(client, "amara")
    ref = client.post("/api/billing/subscription/checkout", headers=amara,
                      json={"plan": "annual", "currency": "KES"}
                      ).get_json()["checkout_url"].rsplit("/", 1)[-1]
    client.post("/api/billing/webhooks/stripe", json={
        "type": "checkout.session.completed", "data": {"object": {"id": ref}}})
    assert client.get("/api/billing/subscription",
                      headers=amara).get_json()["premium"] is True


def test_failed_webhook_does_not_activate(client):
    amara = tok(client, "amara")
    ref = client.post("/api/billing/subscription/checkout", headers=amara,
                      json={"plan": "monthly", "currency": "KES"}
                      ).get_json()["checkout_url"].rsplit("/", 1)[-1]
    client.post("/api/billing/webhooks/stripe", json={
        "type": "checkout.session.expired", "data": {"object": {"id": ref}}})
    assert client.get("/api/billing/subscription",
                      headers=amara).get_json()["premium"] is False


def test_webhook_is_idempotent(client):
    """Stripe retries on a non-2xx. A replay must not extend the period twice."""
    amara = tok(client, "amara")
    ref = client.post("/api/billing/subscription/checkout", headers=amara,
                      json={"plan": "monthly", "currency": "KES"}
                      ).get_json()["checkout_url"].rsplit("/", 1)[-1]
    payload = {"type": "checkout.session.completed", "data": {"object": {"id": ref}}}
    client.post("/api/billing/webhooks/stripe", json=payload)
    first = client.get("/api/billing/subscription",
                       headers=amara).get_json()["subscription"]["current_period_end"]
    client.post("/api/billing/webhooks/stripe", json=payload)   # replay
    second = client.get("/api/billing/subscription",
                        headers=amara).get_json()["subscription"]["current_period_end"]
    assert first == second


def test_unknown_webhook_reference_is_ignored_safely(client):
    r = client.post("/api/billing/webhooks/stripe", json={
        "type": "checkout.session.completed", "data": {"object": {"id": "cs_nope"}}})
    assert r.status_code == 200        # ack anyway so Stripe stops retrying


def test_checkout_rejects_unknown_plan(client):
    amara = tok(client, "amara")
    assert client.post("/api/billing/subscription/checkout", headers=amara,
                       json={"plan": "lifetime"}).status_code == 400


# ------------------------------------------------------------------
# Soft delete behaves like a tombstone, not a hole
# ------------------------------------------------------------------
def test_deleted_journal_entry_disappears_from_listing(client):
    amara = tok(client, "amara")
    child = make_child(client, amara)
    e = client.post(f"/api/pregnancy/children/{child['id']}/journal",
                    headers=amara, json={"body": "temporary"}).get_json()
    assert client.get(f"/api/pregnancy/children/{child['id']}/journal",
                      headers=amara).get_json()["total"] == 1
    client.delete(f"/api/pregnancy/journal/{e['id']}", headers=amara)
    assert client.get(f"/api/pregnancy/children/{child['id']}/journal",
                      headers=amara).get_json()["total"] == 0


# ------------------------------------------------------------------
# Admin privacy boundary: elevated role grants MORE OVERSIGHT,
# not more access to private family memories.
# ------------------------------------------------------------------
def _make_admin(app, role):
    from dearbaby.models import User
    with app.app_context():
        u = User(email=f"{role}@t.test", display_name=role, role=role)
        u.set_password(PW)
        db.session.add(u)
        db.session.commit()


def test_super_admin_cannot_read_a_familys_child(app, client):
    _make_admin(app, "super_admin")
    amara = tok(client, "amara")
    child = make_child(client, amara)
    sup = tok(client, "super_admin")
    # the highest role in the system still gets 404 on someone's memory book
    assert client.get(f"/api/children/{child['id']}", headers=sup).status_code == 404


def test_super_admin_cannot_read_a_familys_journal(app, client):
    _make_admin(app, "super_admin")
    amara = tok(client, "amara")
    child = make_child(client, amara)
    client.post(f"/api/pregnancy/children/{child['id']}/journal", headers=amara,
                json={"body": "Something private about my pregnancy."})
    sup = tok(client, "super_admin")
    assert client.get(f"/api/pregnancy/children/{child['id']}/journal",
                      headers=sup).status_code == 404


def test_super_admin_cannot_read_a_familys_gallery(app, client):
    _make_admin(app, "super_admin")
    amara = tok(client, "amara")
    child = make_child(client, amara)
    sup = tok(client, "super_admin")
    assert client.get(f"/api/media/children/{child['id']}/gallery",
                      headers=sup).status_code == 404


def test_admin_user_detail_shows_counts_but_never_content(app, client):
    _make_admin(app, "super_admin")
    amara = tok(client, "amara")
    child = make_child(client, amara)
    client.post(f"/api/pregnancy/children/{child['id']}/journal", headers=amara,
                json={"title": "Secret", "body": "Deeply private text."})
    amara_id = client.get("/api/auth/me", headers=amara).get_json()["user"]["id"]

    sup = tok(client, "super_admin")
    r = client.get(f"/api/admin/users/{amara_id}", headers=sup)
    assert r.status_code == 200
    body = r.get_json()

    # the admin CAN see that activity exists
    assert body["activity"]["children"] == 1
    assert body["activity"]["journal_entries"] == 1

    # but the content is nowhere in the payload
    raw = r.get_data(as_text=True)
    assert "Deeply private text" not in raw
    assert "Secret" not in raw


def test_parent_cannot_open_admin_user_detail(app, client):
    _make_admin(app, "super_admin")
    amara = tok(client, "amara")
    amara_id = client.get("/api/auth/me", headers=amara).get_json()["user"]["id"]
    assert client.get(f"/api/admin/users/{amara_id}", headers=amara).status_code == 403
