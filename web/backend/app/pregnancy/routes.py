"""Pregnancy journey: weekly tracker, journal, appointments, kicks, contractions."""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import (PregnancyWeek, JournalEntry, Appointment, KickSession,
                        Contraction, Child)
from app.decorators import login_required, _current_user
from app.helpers import (json_body, parse_date, parse_dt, get_child_or_403,
                         paginate, attach_media, media_for)

pregnancy_bp = Blueprint("pregnancy", __name__)


@pregnancy_bp.get("/weeks")
def all_weeks():
    return jsonify(weeks=[w.to_dict() for w in
                          PregnancyWeek.query.order_by(PregnancyWeek.week).all()]), 200


@pregnancy_bp.get("/weeks/<int:week>")
def one_week(week):
    w = db.session.get(PregnancyWeek, week)
    if w is None:
        return jsonify(error="No content for that week"), 404
    return jsonify(w.to_dict()), 200


# ------------------------------------------------------------- journal
@pregnancy_bp.get("/children/<child_id>/journal")
@login_required
def list_journal(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    q = (JournalEntry.alive().filter_by(child_id=child_id)
         .order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()))
    items, meta = paginate(q)
    return jsonify(entries=[e.to_dict(media_for("journal", e.id)) for e in items],
                   **meta), 200


@pregnancy_bp.post("/children/<child_id>/journal")
@login_required
def create_journal(child_id):
    user = _current_user()
    child, err = get_child_or_403(child_id, user, need_edit=True)
    if err: return err
    d = json_body()
    if not (d.get("body") or "").strip():
        return jsonify(error="Write something first"), 400
    e = JournalEntry(child_id=child_id, author_id=user.id,
                     title=(d.get("title") or "").strip() or None,
                     body=d["body"].strip(), mood=d.get("mood"),
                     week=d.get("week") or child.current_week(),
                     entry_date=parse_date(d.get("entry_date")) or None)
    if e.entry_date is None:
        from datetime import date
        e.entry_date = date.today()
    db.session.add(e)
    db.session.flush()
    attach_media("journal", e.id, d.get("media_ids"))
    db.session.commit()
    return jsonify(e.to_dict(media_for("journal", e.id))), 201


@pregnancy_bp.patch("/journal/<entry_id>")
@login_required
def update_journal(entry_id):
    e = JournalEntry.alive().filter_by(id=entry_id).first()
    if e is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(e.child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    for f in ("title", "body", "mood"):
        if f in d: setattr(e, f, d[f])
    db.session.commit()
    return jsonify(e.to_dict(media_for("journal", e.id))), 200


@pregnancy_bp.delete("/journal/<entry_id>")
@login_required
def delete_journal(entry_id):
    e = JournalEntry.alive().filter_by(id=entry_id).first()
    if e is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(e.child_id, _current_user(), need_edit=True)
    if err: return err
    e.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(ok=True), 200


# -------------------------------------------------------- appointments
@pregnancy_bp.get("/children/<child_id>/appointments")
@login_required
def list_appointments(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    items = (Appointment.alive().filter_by(child_id=child_id)
             .order_by(Appointment.starts_at).all())
    return jsonify(appointments=[a.to_dict() for a in items]), 200


@pregnancy_bp.post("/children/<child_id>/appointments")
@login_required
def create_appointment(child_id):
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    starts = parse_dt(d.get("starts_at"))
    if not d.get("title") or not starts:
        return jsonify(error="Title and date/time are required"), 400
    a = Appointment(child_id=child_id, title=d["title"].strip(),
                    location=d.get("location"), notes=d.get("notes"), starts_at=starts)
    db.session.add(a); db.session.commit()
    return jsonify(a.to_dict()), 201


@pregnancy_bp.delete("/appointments/<appt_id>")
@login_required
def delete_appointment(appt_id):
    a = Appointment.alive().filter_by(id=appt_id).first()
    if a is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(a.child_id, _current_user(), need_edit=True)
    if err: return err
    a.deleted_at = datetime.now(timezone.utc); db.session.commit()
    return jsonify(ok=True), 200


# ---------------------------------------------------------- kick counter
@pregnancy_bp.get("/children/<child_id>/kicks")
@login_required
def list_kicks(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    items = (KickSession.alive().filter_by(child_id=child_id)
             .order_by(KickSession.started_at.desc()).limit(30).all())
    return jsonify(sessions=[s.to_dict() for s in items]), 200


@pregnancy_bp.post("/children/<child_id>/kicks")
@login_required
def save_kick_session(child_id):
    """The client counts locally and posts the finished session."""
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    s = KickSession(child_id=child_id, kick_count=int(d.get("kick_count") or 0),
                    started_at=parse_dt(d.get("started_at")) or datetime.now(timezone.utc),
                    ended_at=parse_dt(d.get("ended_at")) or datetime.now(timezone.utc))
    db.session.add(s); db.session.commit()
    return jsonify(s.to_dict()), 201


# ------------------------------------------------------ contraction timer
@pregnancy_bp.get("/children/<child_id>/contractions")
@login_required
def list_contractions(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    items = (Contraction.alive().filter_by(child_id=child_id)
             .order_by(Contraction.started_at.desc()).limit(50).all())
    out = [c.to_dict() for c in items]
    # interval to the previous contraction, computed at read time
    for i in range(len(out) - 1):
        cur = datetime.fromisoformat(out[i]["started_at"])
        prev = datetime.fromisoformat(out[i + 1]["started_at"])
        out[i]["interval_s"] = int((cur - prev).total_seconds())
    return jsonify(contractions=out), 200


@pregnancy_bp.post("/children/<child_id>/contractions")
@login_required
def log_contraction(child_id):
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    started = parse_dt(d.get("started_at"))
    if not started:
        return jsonify(error="started_at is required"), 400
    c = Contraction(child_id=child_id, started_at=started,
                    ended_at=parse_dt(d.get("ended_at")))
    db.session.add(c); db.session.commit()
    return jsonify(c.to_dict()), 201
