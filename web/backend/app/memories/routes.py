"""Baby memory book: milestones, birth record, teeth, growth, timeline,
scrapbook pages and printable books."""
from datetime import datetime, timezone, date
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import (Milestone, MilestoneType, BirthRecord, Tooth, Growth,
                        JournalEntry, Media, ScrapbookPage, PrintBook)
from app.decorators import login_required, _current_user
from app.helpers import (json_body, parse_date, parse_dt, get_child_or_403,
                         attach_media, media_for, premium_required)

memories_bp = Blueprint("memories", __name__)


@memories_bp.get("/milestone-types")
def milestone_types():
    stage = request.args.get("stage")
    q = MilestoneType.query
    if stage: q = q.filter_by(stage=stage)
    return jsonify(types=[t.to_dict() for t in q.order_by(MilestoneType.sort_order).all()]), 200


# ---------------------------------------------------------- milestones
@memories_bp.get("/children/<child_id>/milestones")
@login_required
def list_milestones(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    items = (Milestone.alive().filter_by(child_id=child_id)
             .order_by(Milestone.occurred_on.desc().nullslast(),
                       Milestone.created_at.desc()).all())
    return jsonify(milestones=[m.to_dict(media_for("milestone", m.id)) for m in items]), 200


@memories_bp.post("/children/<child_id>/milestones")
@login_required
def create_milestone(child_id):
    """Unlimited milestone entries — built-in types or a custom title."""
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    title = (d.get("title") or "").strip()
    type_id = d.get("type_id")
    if not title and type_id:
        t = db.session.get(MilestoneType, type_id)
        if t: title, emoji = t.label, t.emoji
        else: return jsonify(error="Unknown milestone type"), 400
    else:
        emoji = d.get("emoji") or "âœ¨"
    if not title:
        return jsonify(error="Give the milestone a name"), 400
    m = Milestone(child_id=child_id, type_id=type_id, title=title,
                  note=d.get("note"), emoji=emoji,
                  occurred_on=parse_date(d.get("occurred_on")) or date.today())
    db.session.add(m); db.session.flush()
    attach_media("milestone", m.id, d.get("media_ids"))
    db.session.commit()
    return jsonify(m.to_dict(media_for("milestone", m.id))), 201


@memories_bp.patch("/milestones/<mid>")
@login_required
def update_milestone(mid):
    m = Milestone.alive().filter_by(id=mid).first()
    if m is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(m.child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    for f in ("title", "note", "emoji"):
        if f in d: setattr(m, f, d[f])
    if "occurred_on" in d: m.occurred_on = parse_date(d["occurred_on"])
    if "media_ids" in d: attach_media("milestone", m.id, d["media_ids"])
    db.session.commit()
    return jsonify(m.to_dict(media_for("milestone", m.id))), 200


@memories_bp.delete("/milestones/<mid>")
@login_required
def delete_milestone(mid):
    m = Milestone.alive().filter_by(id=mid).first()
    if m is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(m.child_id, _current_user(), need_edit=True)
    if err: return err
    m.deleted_at = datetime.now(timezone.utc); db.session.commit()
    return jsonify(ok=True), 200


# -------------------------------------------------------- birth record
@memories_bp.get("/children/<child_id>/birth-record")
@login_required
def get_birth(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    r = db.session.get(BirthRecord, child_id)
    return jsonify(r.to_dict() if r else {"child_id": child_id}), 200


@memories_bp.put("/children/<child_id>/birth-record")
@login_required
def put_birth(child_id):
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    r = db.session.get(BirthRecord, child_id) or BirthRecord(child_id=child_id)
    r.born_at = parse_dt(d.get("born_at")) or r.born_at
    for f in ("place", "notes"):
        if f in d: setattr(r, f, d[f])
    for f in ("weight_g", "length_cm", "head_circ_cm"):
        if d.get(f) is not None: setattr(r, f, float(d[f]))
    db.session.add(r); db.session.commit()
    return jsonify(r.to_dict()), 200


# --------------------------------------------------------------- teeth
TOOTH_CODES = [f"{a}_{b}" for a in ("upper", "lower")
               for b in ("right_second_molar", "right_first_molar", "right_canine",
                         "right_lateral", "right_central", "left_central",
                         "left_lateral", "left_canine", "left_first_molar",
                         "left_second_molar")]


@memories_bp.get("/children/<child_id>/teeth")
@login_required
def list_teeth(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    rows = {t.tooth_code: t for t in Tooth.query.filter_by(child_id=child_id).all()}
    return jsonify(teeth=[{"tooth_code": c,
                           "erupted_on": rows[c].erupted_on.isoformat()
                           if c in rows and rows[c].erupted_on else None,
                           "id": rows[c].id if c in rows else None}
                          for c in TOOTH_CODES]), 200


@memories_bp.post("/children/<child_id>/teeth")
@login_required
def set_tooth(child_id):
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    code = d.get("tooth_code")
    if code not in TOOTH_CODES:
        return jsonify(error="Unknown tooth"), 400
    t = Tooth.query.filter_by(child_id=child_id, tooth_code=code).first()
    when = parse_date(d.get("erupted_on"))
    if when is None:                       # toggling it off
        if t: db.session.delete(t)
        db.session.commit()
        return jsonify(tooth_code=code, erupted_on=None), 200
    if t is None:
        t = Tooth(child_id=child_id, tooth_code=code)
        db.session.add(t)
    t.erupted_on = when
    db.session.commit()
    return jsonify(t.to_dict()), 200


# -------------------------------------------------------------- growth
@memories_bp.get("/children/<child_id>/growth")
@login_required
def list_growth(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    q = Growth.alive().filter_by(child_id=child_id)
    kind = request.args.get("kind")
    if kind: q = q.filter_by(kind=kind)
    return jsonify(measurements=[g.to_dict() for g in
                                 q.order_by(Growth.measured_on).all()]), 200


@memories_bp.post("/children/<child_id>/growth")
@login_required
def add_growth(child_id):
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    if d.get("kind") not in ("height", "weight", "head"):
        return jsonify(error="kind must be height, weight or head"), 400
    try:
        value = float(d.get("value"))
    except (TypeError, ValueError):
        return jsonify(error="A numeric value is required"), 400
    g = Growth(child_id=child_id, kind=d["kind"], value=value,
               measured_on=parse_date(d.get("measured_on")) or date.today())
    db.session.add(g); db.session.commit()
    return jsonify(g.to_dict()), 201


@memories_bp.delete("/growth/<gid>")
@login_required
def delete_growth(gid):
    g = Growth.alive().filter_by(id=gid).first()
    if g is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(g.child_id, _current_user(), need_edit=True)
    if err: return err
    g.deleted_at = datetime.now(timezone.utc); db.session.commit()
    return jsonify(ok=True), 200


# ------------------------------------------------------------ timeline
@memories_bp.get("/children/<child_id>/timeline")
@login_required
def timeline(child_id):
    """Merged, date-ordered feed of everything recorded for this child."""
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    events = []
    for m in Milestone.alive().filter_by(child_id=child_id).all():
        events.append({"type": "milestone", "date": m.occurred_on.isoformat()
                       if m.occurred_on else m.created_at.date().isoformat(),
                       "title": m.title, "emoji": m.emoji or "âœ¨", "note": m.note,
                       "id": m.id, "media": media_for("milestone", m.id)})
    for j in JournalEntry.alive().filter_by(child_id=child_id).all():
        events.append({"type": "journal", "date": j.entry_date.isoformat(),
                       "title": j.title or "Journal entry", "emoji": "ðŸ“", "note": j.body,
                       "id": j.id, "media": media_for("journal", j.id)})
    for g in Growth.alive().filter_by(child_id=child_id).all():
        unit = "kg" if g.kind == "weight" else "cm"
        events.append({"type": "growth", "date": g.measured_on.isoformat(),
                       "title": f"{g.kind.title()}: {g.value}{unit}", "emoji": "ðŸ“",
                       "note": None, "id": g.id, "media": []})
    events.sort(key=lambda e: e["date"], reverse=True)
    return jsonify(timeline=events), 200


# ------------------------------------------------ scrapbook & print books
@memories_bp.get("/children/<child_id>/scrapbook")
@login_required
def list_pages(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    pages = (ScrapbookPage.alive().filter_by(child_id=child_id)
             .order_by(ScrapbookPage.position).all())
    return jsonify(pages=[p.to_dict() for p in pages]), 200


@memories_bp.post("/children/<child_id>/scrapbook")
@login_required
def create_page(child_id):
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    n = ScrapbookPage.alive().filter_by(child_id=child_id).count()
    p = ScrapbookPage(child_id=child_id, title=d.get("title") or f"Page {n + 1}",
                      layout=d.get("layout") or {"elements": []},
                      theme=d.get("theme") or "oat", position=n)
    db.session.add(p); db.session.commit()
    return jsonify(p.to_dict()), 201


@memories_bp.patch("/scrapbook/<pid>")
@login_required
def update_page(pid):
    p = ScrapbookPage.alive().filter_by(id=pid).first()
    if p is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(p.child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    for f in ("title", "layout", "theme", "position"):
        if f in d: setattr(p, f, d[f])
    db.session.commit()
    return jsonify(p.to_dict()), 200


@memories_bp.get("/children/<child_id>/print-books")
@login_required
def list_books(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    books = PrintBook.alive().filter_by(child_id=child_id).all()
    return jsonify(books=[b.to_dict() for b in books]), 200


@memories_bp.post("/children/<child_id>/print-books")
@login_required
@premium_required
def create_book(child_id):
    """Premium. Compiles scrapbook pages into a book record; rendering the
    PDF is a background job — see the INTEGRATION POINT below."""
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    b = PrintBook(child_id=child_id, title=d.get("title") or "My Memory Book",
                  page_ids=d.get("page_ids") or [], status="draft")
    db.session.add(b); db.session.commit()
    return jsonify(b.to_dict()), 201


@memories_bp.post("/print-books/<bid>/render")
@login_required
@premium_required
def render_book(bid):
    b = PrintBook.alive().filter_by(id=bid).first()
    if b is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(b.child_id, _current_user(), need_edit=True)
    if err: return err
    # ---- INTEGRATION POINT: PDF rendering -----------------------------
    # Queue a background job that renders each scrapbook page's layout JSON
    # to a print-ready PDF (300dpi, bleed) and stores the URL on the record.
    # Scaffolded, not wired: the status moves to "rendering" and stops there.
    b.status = "rendering"
    db.session.commit()
    return jsonify(b.to_dict(), ), 202
