"""Children: the subject every memory hangs off. Also co-parent sharing."""
from flask import Blueprint, jsonify
from dearbaby.extensions import db
from dearbaby.models import Child, ChildMember, User, Milestone, JournalEntry, Media
from dearbaby.decorators import login_required, _current_user
from dearbaby.helpers import json_body, parse_date, get_child_or_403

children_bp = Blueprint("children", __name__)


@children_bp.get("")
@login_required
def list_children():
    user = _current_user()
    owned = Child.alive().filter_by(owner_id=user.id).all()
    shared_ids = [m.child_id for m in ChildMember.query.filter_by(user_id=user.id).all()]
    shared = Child.alive().filter(Child.id.in_(shared_ids)).all() if shared_ids else []
    return jsonify(children=[c.to_dict() for c in owned + shared]), 200


@children_bp.post("")
@login_required
def create_child():
    user = _current_user()
    d = json_body()
    if not d.get("due_date") and not d.get("birth_date"):
        return jsonify(error="Give a due date or a birth date"), 400
    child = Child(owner_id=user.id, name=(d.get("name") or "").strip() or None,
                  due_date=parse_date(d.get("due_date")),
                  birth_date=parse_date(d.get("birth_date")),
                  sex=d.get("sex"))
    db.session.add(child)
    db.session.commit()
    return jsonify(child.to_dict()), 201


@children_bp.get("/<child_id>")
@login_required
def get_child(child_id):
    child, err = get_child_or_403(child_id, _current_user())
    if err: return err
    return jsonify(child.to_dict()), 200


@children_bp.patch("/<child_id>")
@login_required
def update_child(child_id):
    child, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    for f in ("name", "sex", "cover_url"):
        if f in d: setattr(child, f, d[f])
    if "due_date" in d: child.due_date = parse_date(d["due_date"])
    if "birth_date" in d: child.birth_date = parse_date(d["birth_date"])
    db.session.commit()
    return jsonify(child.to_dict()), 200


@children_bp.delete("/<child_id>")
@login_required
def delete_child(child_id):
    from datetime import datetime, timezone
    user = _current_user()
    child, err = get_child_or_403(child_id, user)
    if err: return err
    if child.owner_id != user.id:
        return jsonify(error="Only the owner can delete this"), 403
    child.deleted_at = datetime.now(timezone.utc)   # soft delete, syncs as a tombstone
    db.session.commit()
    return jsonify(ok=True), 200


@children_bp.get("/<child_id>/members")
@login_required
def list_members(child_id):
    child, err = get_child_or_403(child_id, _current_user())
    if err: return err
    rows = ChildMember.query.filter_by(child_id=child_id).all()
    users = {u.id: u for u in User.query.filter(
        User.id.in_([r.user_id for r in rows] + [child.owner_id])).all()}
    out = [{"user": users[child.owner_id].public(), "can_edit": True, "owner": True}]
    out += [{"user": users[r.user_id].public(), "can_edit": r.can_edit, "owner": False}
            for r in rows if r.user_id in users]
    return jsonify(members=out), 200


@children_bp.post("/<child_id>/members")
@login_required
def add_member(child_id):
    user = _current_user()
    child, err = get_child_or_403(child_id, user)
    if err: return err
    if child.owner_id != user.id:
        return jsonify(error="Only the owner can invite family"), 403
    d = json_body()
    invitee = User.query.filter_by(email=(d.get("email") or "").strip().lower()).first()
    if invitee is None:
        return jsonify(error="No DearBaby account with that email yet"), 404
    if invitee.id == user.id:
        return jsonify(error="You already have access"), 400
    if ChildMember.query.filter_by(child_id=child_id, user_id=invitee.id).first():
        return jsonify(error="They already have access"), 409
    db.session.add(ChildMember(child_id=child_id, user_id=invitee.id,
                               can_edit=bool(d.get("can_edit"))))
    db.session.commit()
    return jsonify(user=invitee.public(), can_edit=bool(d.get("can_edit"))), 201


@children_bp.delete("/<child_id>/members/<user_id>")
@login_required
def remove_member(child_id, user_id):
    user = _current_user()
    child, err = get_child_or_403(child_id, user)
    if err: return err
    if child.owner_id != user.id:
        return jsonify(error="Only the owner can remove family"), 403
    ChildMember.query.filter_by(child_id=child_id, user_id=user_id).delete()
    db.session.commit()
    return jsonify(ok=True), 200


@children_bp.get("/<child_id>/summary")
@login_required
def summary(child_id):
    """Dashboard payload: one call instead of six."""
    child, err = get_child_or_403(child_id, _current_user())
    if err: return err
    return jsonify(
        child=child.to_dict(),
        counts={
            "milestones": Milestone.alive().filter_by(child_id=child_id).count(),
            "journal": JournalEntry.alive().filter_by(child_id=child_id).count(),
            "media": Media.alive().filter_by(child_id=child_id).count(),
        }), 200
