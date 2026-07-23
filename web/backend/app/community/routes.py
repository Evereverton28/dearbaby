"""Community: groups, discussions, Q&A, likes, comments, follows, reporting."""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app.extensions import db
from app.models import (Group, GroupMember, Post, Comment, Like, Follow,
                        Report, User)
from app.decorators import login_required, _current_user
from app.helpers import json_body, paginate

community_bp = Blueprint("community", __name__)


def _liked_ids(user_id, entity_type, ids):
    if not ids: return set()
    rows = Like.query.filter(Like.user_id == user_id,
                             Like.entity_type == entity_type,
                             Like.entity_id.in_(ids)).all()
    return {r.entity_id for r in rows}


@community_bp.get("/groups")
def list_groups():
    out = []
    for g in Group.alive().all():
        out.append(g.to_dict(
            GroupMember.query.filter_by(group_id=g.id).count(),
            Post.alive().filter_by(group_id=g.id, status="visible").count()))
    return jsonify(groups=out), 200


@community_bp.post("/groups/<gid>/join")
@login_required
def join_group(gid):
    user = _current_user()
    if not GroupMember.query.filter_by(group_id=gid, user_id=user.id).first():
        db.session.add(GroupMember(group_id=gid, user_id=user.id))
        db.session.commit()
    return jsonify(ok=True, joined=True), 200


@community_bp.delete("/groups/<gid>/join")
@login_required
def leave_group(gid):
    GroupMember.query.filter_by(group_id=gid, user_id=_current_user().id).delete()
    db.session.commit()
    return jsonify(ok=True, joined=False), 200


@community_bp.get("/posts")
@login_required
def list_posts():
    """Feed. ?group=<id> to scope, ?kind=question for Q&A, ?following=1 for
    posts by people you follow."""
    user = _current_user()
    q = Post.alive().filter_by(status="visible")
    if request.args.get("group"):
        q = q.filter_by(group_id=request.args["group"])
    if request.args.get("kind"):
        q = q.filter_by(kind=request.args["kind"])
    if request.args.get("following") == "1":
        ids = [f.followee_id for f in Follow.query.filter_by(follower_id=user.id).all()]
        q = q.filter(Post.author_id.in_(ids or ["__none__"]))
    q = q.order_by(Post.created_at.desc())
    items, meta = paginate(q, default=20)

    authors = {u.id: u for u in User.query.filter(
        User.id.in_([p.author_id for p in items] or ["__none__"])).all()}
    groups = {g.id: g for g in Group.query.filter(
        Group.id.in_([p.group_id for p in items if p.group_id] or ["__none__"])).all()}
    liked = _liked_ids(user.id, "post", [p.id for p in items])
    return jsonify(posts=[p.to_dict(authors.get(p.author_id),
                                    groups.get(p.group_id), p.id in liked)
                          for p in items], **meta), 200


@community_bp.post("/posts")
@login_required
def create_post():
    user = _current_user()
    d = json_body()
    body = (d.get("body") or "").strip()
    if len(body) < 2:
        return jsonify(error="Write a little more before posting"), 400
    p = Post(author_id=user.id, group_id=d.get("group_id"),
             kind=d.get("kind") if d.get("kind") in ("discussion", "question") else "discussion",
             title=(d.get("title") or "").strip() or None, body=body)
    db.session.add(p); db.session.commit()
    return jsonify(p.to_dict(user, db.session.get(Group, p.group_id) if p.group_id else None)), 201


@community_bp.get("/posts/<pid>")
@login_required
def get_post(pid):
    user = _current_user()
    p = Post.alive().filter_by(id=pid).first()
    if p is None or p.status != "visible":
        return jsonify(error="This post isn't available"), 404
    author = db.session.get(User, p.author_id)
    group = db.session.get(Group, p.group_id) if p.group_id else None
    comments = (Comment.alive().filter_by(post_id=pid, status="visible")
                .order_by(Comment.created_at).all())
    cauthors = {u.id: u for u in User.query.filter(
        User.id.in_([c.author_id for c in comments] or ["__none__"])).all()}
    liked = _liked_ids(user.id, "post", [pid])
    return jsonify(post=p.to_dict(author, group, pid in liked),
                   comments=[c.to_dict(cauthors.get(c.author_id)) for c in comments]), 200


@community_bp.post("/posts/<pid>/comments")
@login_required
def add_comment(pid):
    user = _current_user()
    p = Post.alive().filter_by(id=pid).first()
    if p is None: return jsonify(error="Not found"), 404
    body = (json_body().get("body") or "").strip()
    if not body: return jsonify(error="Write a reply first"), 400
    c = Comment(post_id=pid, author_id=user.id, body=body)
    p.reply_count = (p.reply_count or 0) + 1
    db.session.add(c); db.session.commit()
    return jsonify(c.to_dict(user)), 201


@community_bp.post("/likes")
@login_required
def toggle_like():
    """Idempotent toggle; returns the new state and count."""
    user = _current_user()
    d = json_body()
    etype, eid = d.get("entity_type"), d.get("entity_id")
    if etype not in ("post", "comment") or not eid:
        return jsonify(error="entity_type and entity_id are required"), 400
    row = Like.query.filter_by(user_id=user.id, entity_type=etype, entity_id=eid).first()
    target = (Post.alive().filter_by(id=eid).first() if etype == "post"
              else Comment.alive().filter_by(id=eid).first())
    if target is None: return jsonify(error="Not found"), 404
    if row:
        db.session.delete(row)
        target.like_count = max(0, (target.like_count or 0) - 1)
        liked = False
    else:
        db.session.add(Like(user_id=user.id, entity_type=etype, entity_id=eid))
        target.like_count = (target.like_count or 0) + 1
        liked = True
    db.session.commit()
    return jsonify(liked=liked, like_count=target.like_count), 200


@community_bp.post("/follows/<user_id>")
@login_required
def toggle_follow(user_id):
    me = _current_user()
    if user_id == me.id:
        return jsonify(error="You can't follow yourself"), 400
    if db.session.get(User, user_id) is None:
        return jsonify(error="Not found"), 404
    row = Follow.query.filter_by(follower_id=me.id, followee_id=user_id).first()
    if row:
        db.session.delete(row); following = False
    else:
        db.session.add(Follow(follower_id=me.id, followee_id=user_id)); following = True
    db.session.commit()
    return jsonify(following=following), 200


@community_bp.get("/users/<user_id>")
@login_required
def user_profile(user_id):
    me = _current_user()
    u = db.session.get(User, user_id)
    if u is None or not u.is_active:
        return jsonify(error="Not found"), 404
    posts = (Post.alive().filter_by(author_id=user_id, status="visible")
             .order_by(Post.created_at.desc()).limit(20).all())
    return jsonify(
        user={**u.public(), "bio": u.bio},
        following=bool(Follow.query.filter_by(follower_id=me.id, followee_id=user_id).first()),
        follower_count=Follow.query.filter_by(followee_id=user_id).count(),
        following_count=Follow.query.filter_by(follower_id=user_id).count(),
        posts=[p.to_dict(u) for p in posts]), 200


@community_bp.post("/reports")
@login_required
def report_content():
    user = _current_user()
    d = json_body()
    if d.get("entity_type") not in ("post", "comment", "user"):
        return jsonify(error="Unsupported report type"), 400
    r = Report(reporter_id=user.id, entity_type=d["entity_type"],
               entity_id=d.get("entity_id"), reason=(d.get("reason") or "").strip())
    db.session.add(r); db.session.commit()
    return jsonify(ok=True, id=r.id), 201
