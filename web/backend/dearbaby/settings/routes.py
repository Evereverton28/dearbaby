"""Settings, data export and account deletion (Kenya DPA 2019 / GDPR)."""
from datetime import datetime, timezone
from flask import Blueprint, jsonify
from dearbaby.extensions import db
from dearbaby.models import (UserSettings, User, Child, JournalEntry, Milestone,
                        Growth, Media, Album, Post, Comment, Reminder,
                        Notification, Appointment, BirthRecord, Tooth)
from dearbaby.decorators import login_required, _current_user
from dearbaby.helpers import json_body, media_for

settings_bp = Blueprint("settings", __name__)

FIELDS = ("theme", "notif_milestones", "notif_pregnancy", "notif_vaccination",
          "notif_birthday", "notif_growth", "auto_backup", "units", "profile_public")


def _settings_for(user_id):
    s = db.session.get(UserSettings, user_id)
    if s is None:
        s = UserSettings(user_id=user_id)
        db.session.add(s)
        db.session.commit()
    return s


@settings_bp.get("")
@login_required
def get_settings():
    return jsonify(_settings_for(_current_user().id).to_dict()), 200


@settings_bp.patch("")
@login_required
def update_settings():
    s = _settings_for(_current_user().id)
    d = json_body()
    for f in FIELDS:
        if f in d:
            setattr(s, f, d[f])
    db.session.commit()
    return jsonify(s.to_dict()), 200


@settings_bp.patch("/profile")
@login_required
def update_profile():
    user = _current_user()
    d = json_body()
    if "display_name" in d and (d["display_name"] or "").strip():
        user.display_name = d["display_name"].strip()
    if "bio" in d: user.bio = d["bio"]
    if "avatar_url" in d: user.avatar_url = d["avatar_url"]
    db.session.commit()
    return jsonify(user.to_dict(full=True)), 200


@settings_bp.post("/password")
@login_required
def change_password():
    user = _current_user()
    d = json_body()
    if not user.check_password(d.get("current_password") or ""):
        return jsonify(error="That's not your current password"), 400
    new = d.get("new_password") or ""
    if len(new) < 8:
        return jsonify(error="Use at least 8 characters"), 400
    user.set_password(new)
    db.session.commit()
    return jsonify(ok=True), 200


@settings_bp.get("/export")
@login_required
def export_everything():
    """
    Full data export. Returns JSON directly; for large accounts this should
    become a background job that emails a download link.
    """
    user = _current_user()
    children = Child.alive().filter_by(owner_id=user.id).all()
    out = {"exported_at": datetime.now(timezone.utc).isoformat(),
           "account": user.to_dict(full=True),
           "settings": _settings_for(user.id).to_dict(),
           "children": []}
    for c in children:
        birth = db.session.get(BirthRecord, c.id)
        out["children"].append({
            "child": c.to_dict(),
            "birth_record": birth.to_dict() if birth else None,
            "journal": [j.to_dict(media_for("journal", j.id))
                        for j in JournalEntry.alive().filter_by(child_id=c.id).all()],
            "milestones": [m.to_dict(media_for("milestone", m.id))
                           for m in Milestone.alive().filter_by(child_id=c.id).all()],
            "growth": [g.to_dict() for g in Growth.alive().filter_by(child_id=c.id).all()],
            "teeth": [t.to_dict() for t in Tooth.query.filter_by(child_id=c.id).all()],
            "appointments": [a.to_dict() for a in
                             Appointment.alive().filter_by(child_id=c.id).all()],
            "media": [m.to_dict() for m in Media.alive().filter_by(child_id=c.id).all()],
            "albums": [a.to_dict() for a in Album.alive().filter_by(child_id=c.id).all()],
        })
    out["community"] = {
        "posts": [p.to_dict(user) for p in Post.alive().filter_by(author_id=user.id).all()],
        "comments": [c.to_dict(user) for c in Comment.alive().filter_by(author_id=user.id).all()],
    }
    return jsonify(out), 200


@settings_bp.delete("/account")
@login_required
def delete_account():
    """
    Hard-deletes the account and everything hanging off it. Requires the
    password so a stolen session can't wipe someone's memories.
    """
    user = _current_user()
    d = json_body()
    if not user.check_password(d.get("password") or ""):
        return jsonify(error="Enter your password to confirm"), 400

    child_ids = [c.id for c in Child.query.filter_by(owner_id=user.id).all()]
    if child_ids:
        for model in (JournalEntry, Milestone, Growth, Media, Album,
                      Appointment, Tooth):
            model.query.filter(model.child_id.in_(child_ids)).delete(synchronize_session=False)
        BirthRecord.query.filter(BirthRecord.child_id.in_(child_ids)).delete(
            synchronize_session=False)
        Child.query.filter(Child.id.in_(child_ids)).delete(synchronize_session=False)

    for model in (Post, Comment, Reminder, Notification):
        col = model.author_id if hasattr(model, "author_id") else model.user_id
        model.query.filter(col == user.id).delete(synchronize_session=False)
    UserSettings.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify(ok=True, message="Your account and all memories were deleted"), 200
