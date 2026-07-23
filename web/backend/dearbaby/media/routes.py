"""Media upload, gallery grouping, albums and family sharing.

Dev stores files on local disk under instance/uploads. In production swap
_save_file() for a signed-URL handshake against R2/S3 — the routes and the
client contract stay identical.
"""
import os, secrets
from datetime import datetime, timezone, timedelta
from collections import OrderedDict
from flask import Blueprint, jsonify, request, current_app, send_from_directory
from werkzeug.utils import secure_filename
from dearbaby.extensions import db
from dearbaby.models import Media, Album, AlbumMedia, Share, Child
from dearbaby.decorators import login_required, _current_user
from dearbaby.helpers import json_body, get_child_or_403, paginate

media_bp = Blueprint("media", __name__)

ALLOWED = {"jpg", "jpeg", "png", "gif", "webp", "heic",
           "mp4", "mov", "webm", "pdf"}
MAX_BYTES = 50 * 1024 * 1024


def _upload_dir():
    d = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(d, exist_ok=True)
    return d


def _kind_for(ext):
    if ext in ("mp4", "mov", "webm"): return "video"
    if ext == "pdf": return "document"
    return "photo"


@media_bp.post("/upload")
@login_required
def upload():
    user = _current_user()
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify(error="Choose a file to upload"), 400

    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED:
        return jsonify(error=f"{ext or 'That file type'} isn't supported"), 415

    child_id = request.form.get("child_id")
    if child_id:
        _, err = get_child_or_403(child_id, user, need_edit=True)
        if err: return err

    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    if size > MAX_BYTES:
        return jsonify(error="Files must be under 50MB"), 413

    m = Media(owner_id=user.id, child_id=child_id,
              kind=request.form.get("kind") or _kind_for(ext),
              filename=secure_filename(f.filename), mime_type=f.mimetype, bytes=size,
              caption=request.form.get("caption"))
    db.session.add(m)
    db.session.flush()

    stored = f"{m.id}.{ext}"
    f.save(os.path.join(_upload_dir(), stored))
    m.url = f"/api/media/file/{stored}"
    m.thumb_url = m.url
    db.session.commit()
    return jsonify(m.to_dict()), 201


@media_bp.get("/file/<path:name>")
def serve_file(name):
    # Dev only. In production these are signed, expiring object-storage URLs.
    return send_from_directory(_upload_dir(), name)


@media_bp.get("/children/<child_id>/gallery")
@login_required
def gallery(child_id):
    """Organised by year then month, newest first."""
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    items = (Media.alive().filter_by(child_id=child_id)
             .order_by(Media.captured_at.desc()).all())
    groups = OrderedDict()
    for m in items:
        key = m.captured_at.strftime("%Y-%m") if m.captured_at else "undated"
        groups.setdefault(key, []).append(m.to_dict())
    return jsonify(groups=[{"period": k, "items": v} for k, v in groups.items()],
                   total=len(items)), 200


@media_bp.delete("/<mid>")
@login_required
def delete_media(mid):
    m = Media.alive().filter_by(id=mid).first()
    if m is None: return jsonify(error="Not found"), 404
    user = _current_user()
    if m.owner_id != user.id:
        _, err = get_child_or_403(m.child_id, user, need_edit=True)
        if err: return err
    m.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(ok=True), 200


# --------------------------------------------------------------- albums
@media_bp.get("/children/<child_id>/albums")
@login_required
def list_albums(child_id):
    _, err = get_child_or_403(child_id, _current_user())
    if err: return err
    out = []
    for a in Album.alive().filter_by(child_id=child_id).all():
        out.append(a.to_dict(AlbumMedia.query.filter_by(album_id=a.id).count()))
    return jsonify(albums=out), 200


@media_bp.post("/children/<child_id>/albums")
@login_required
def create_album(child_id):
    _, err = get_child_or_403(child_id, _current_user(), need_edit=True)
    if err: return err
    d = json_body()
    if not (d.get("title") or "").strip():
        return jsonify(error="Give the album a name"), 400
    a = Album(child_id=child_id, title=d["title"].strip())
    db.session.add(a); db.session.commit()
    return jsonify(a.to_dict(0)), 201


@media_bp.get("/albums/<aid>")
@login_required
def album_detail(aid):
    a = Album.alive().filter_by(id=aid).first()
    if a is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(a.child_id, _current_user())
    if err: return err
    rows = AlbumMedia.query.filter_by(album_id=aid).order_by(AlbumMedia.position).all()
    ids = [r.media_id for r in rows]
    items = Media.query.filter(Media.id.in_(ids), Media.deleted_at.is_(None)).all() if ids else []
    return jsonify(album=a.to_dict(len(items)), items=[m.to_dict() for m in items]), 200


@media_bp.post("/albums/<aid>/media")
@login_required
def add_to_album(aid):
    a = Album.alive().filter_by(id=aid).first()
    if a is None: return jsonify(error="Not found"), 404
    _, err = get_child_or_403(a.child_id, _current_user(), need_edit=True)
    if err: return err
    n = AlbumMedia.query.filter_by(album_id=aid).count()
    for i, mid in enumerate(json_body().get("media_ids") or []):
        if not AlbumMedia.query.filter_by(album_id=aid, media_id=mid).first():
            db.session.add(AlbumMedia(album_id=aid, media_id=mid, position=n + i))
    db.session.commit()
    return jsonify(ok=True), 200


# --------------------------------------------------------------- shares
@media_bp.post("/shares")
@login_required
def create_share():
    """A view-only link families can open without an account."""
    user = _current_user()
    d = json_body()
    if d.get("entity_type") not in ("album", "media", "milestone"):
        return jsonify(error="Unsupported share type"), 400
    s = Share(owner_id=user.id, entity_type=d["entity_type"], entity_id=d.get("entity_id"),
              token=secrets.token_urlsafe(16),
              expires_at=datetime.now(timezone.utc) + timedelta(days=int(d.get("days", 30))))
    db.session.add(s); db.session.commit()
    return jsonify(token=s.token, url=f"/shared/{s.token}",
                   expires_at=s.expires_at.isoformat()), 201


@media_bp.get("/shared/<token>")
def view_share(token):
    s = Share.alive().filter_by(token=token).first()
    if s is None:
        return jsonify(error="This link is no longer available"), 404
    if s.expires_at and s.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return jsonify(error="This link has expired"), 410
    if s.entity_type == "album":
        rows = AlbumMedia.query.filter_by(album_id=s.entity_id).all()
        ids = [r.media_id for r in rows]
        items = Media.query.filter(Media.id.in_(ids), Media.deleted_at.is_(None)).all() if ids else []
        album = Album.alive().filter_by(id=s.entity_id).first()
        return jsonify(type="album", title=album.title if album else "Shared album",
                       items=[m.to_dict() for m in items]), 200
    m = Media.alive().filter_by(id=s.entity_id).first()
    return jsonify(type="media", items=[m.to_dict()] if m else []), 200
