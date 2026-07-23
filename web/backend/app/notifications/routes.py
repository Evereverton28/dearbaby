"""Reminders (scheduled) and notifications (delivered)."""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify
from app.extensions import db
from app.models import Reminder, Notification, Child, UserSettings
from app.decorators import login_required, _current_user
from app.helpers import json_body, parse_dt, get_child_or_403

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("")
@login_required
def list_notifications():
    user = _current_user()
    items = (Notification.alive().filter_by(user_id=user.id)
             .order_by(Notification.created_at.desc()).limit(50).all())
    unread = Notification.alive().filter_by(user_id=user.id, read_at=None).count()
    return jsonify(notifications=[n.to_dict() for n in items], unread=unread), 200


@notifications_bp.post("/read")
@login_required
def mark_read():
    user = _current_user()
    d = json_body()
    q = Notification.alive().filter_by(user_id=user.id, read_at=None)
    if d.get("id"):
        q = q.filter_by(id=d["id"])
    for n in q.all():
        n.read_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(ok=True), 200


@notifications_bp.get("/reminders")
@login_required
def list_reminders():
    items = (Reminder.alive().filter_by(user_id=_current_user().id)
             .order_by(Reminder.fire_at).all())
    return jsonify(reminders=[r.to_dict() for r in items]), 200


@notifications_bp.post("/reminders")
@login_required
def create_reminder():
    user = _current_user()
    d = json_body()
    fire = parse_dt(d.get("fire_at"))
    if not d.get("title") or not fire:
        return jsonify(error="Title and date/time are required"), 400
    if d.get("child_id"):
        _, err = get_child_or_403(d["child_id"], user)
        if err: return err
    r = Reminder(user_id=user.id, child_id=d.get("child_id"),
                 kind=d.get("kind") or "custom", title=d["title"].strip(),
                 body=d.get("body"), fire_at=fire)
    db.session.add(r); db.session.commit()
    return jsonify(r.to_dict()), 201


@notifications_bp.delete("/reminders/<rid>")
@login_required
def delete_reminder(rid):
    r = Reminder.alive().filter_by(id=rid, user_id=_current_user().id).first()
    if r is None: return jsonify(error="Not found"), 404
    r.deleted_at = datetime.now(timezone.utc); db.session.commit()
    return jsonify(ok=True), 200


# Kenya's routine childhood immunisation points, in weeks after birth.
VACCINE_SCHEDULE = [(0, "BCG and polio (birth dose)"), (6, "6-week clinic visit"),
                    (10, "10-week clinic visit"), (14, "14-week clinic visit"),
                    (39, "Measles-rubella (9 months)"), (78, "Measles-rubella (18 months)")]


@notifications_bp.post("/children/<child_id>/schedule-defaults")
@login_required
def schedule_defaults(child_id):
    """Generate the standard reminder set for a child in one call: pregnancy
    week check-ins before birth, vaccination and growth reminders after."""
    user = _current_user()
    child, err = get_child_or_403(child_id, user)
    if err: return err
    settings = db.session.get(UserSettings, user.id)
    created = 0

    if child.birth_date:
        base = datetime.combine(child.birth_date, datetime.min.time(), tzinfo=timezone.utc)
        if not settings or settings.notif_vaccination:
            for weeks, label in VACCINE_SCHEDULE:
                when = base + timedelta(weeks=weeks)
                if when < datetime.now(timezone.utc): continue
                db.session.add(Reminder(user_id=user.id, child_id=child_id,
                                        kind="vaccination", title=label,
                                        body="Immunisation due", fire_at=when))
                created += 1
        if not settings or settings.notif_birthday:
            for year in (1, 2, 3):
                when = base.replace(year=base.year + year)
                if when > datetime.now(timezone.utc):
                    db.session.add(Reminder(user_id=user.id, child_id=child_id,
                                            kind="birthday",
                                            title=f"{child.name or 'Baby'} turns {year}",
                                            fire_at=when))
                    created += 1
    elif child.due_date:
        if not settings or settings.notif_pregnancy:
            base = datetime.combine(child.due_date, datetime.min.time(), tzinfo=timezone.utc)
            for wk in range(1, 41):
                when = base - timedelta(weeks=(40 - wk))
                if when < datetime.now(timezone.utc): continue
                db.session.add(Reminder(user_id=user.id, child_id=child_id,
                                        kind="pregnancy_week", title=f"Week {wk}",
                                        body="See what's changing this week",
                                        fire_at=when))
                created += 1
    db.session.commit()
    return jsonify(created=created), 201
