"""Weaning and baby-food recipes: search, filter by age, save favourites."""
from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from app.extensions import db
from app.models import Recipe, RecipeFavorite
from app.decorators import login_required, _current_user
from app.helpers import paginate

recipes_bp = Blueprint("recipes", __name__)


@recipes_bp.get("")
@login_required
def list_recipes():
    user = _current_user()
    q = Recipe.alive()
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Recipe.title.ilike(like), Recipe.description.ilike(like)))
    if request.args.get("category"):
        q = q.filter_by(category=request.args["category"])
    if request.args.get("max_age"):
        q = q.filter(Recipe.min_age_months <= int(request.args["max_age"]))
    if request.args.get("favorites") == "1":
        ids = [f.recipe_id for f in RecipeFavorite.query.filter_by(user_id=user.id).all()]
        q = q.filter(Recipe.id.in_(ids or ["__none__"]))

    items, meta = paginate(q.order_by(Recipe.min_age_months, Recipe.title), default=24)
    favs = {f.recipe_id for f in RecipeFavorite.query.filter_by(user_id=user.id).all()}
    return jsonify(recipes=[r.to_dict(r.id in favs) for r in items], **meta), 200


@recipes_bp.get("/categories")
def categories():
    rows = db.session.query(Recipe.category, db.func.count(Recipe.id)).filter(
        Recipe.deleted_at.is_(None)).group_by(Recipe.category).all()
    return jsonify(categories=[{"key": c, "count": n} for c, n in rows if c]), 200


@recipes_bp.get("/<rid>")
@login_required
def get_recipe(rid):
    r = Recipe.alive().filter_by(id=rid).first()
    if r is None: return jsonify(error="Not found"), 404
    fav = RecipeFavorite.query.filter_by(user_id=_current_user().id, recipe_id=rid).first()
    return jsonify(r.to_dict(bool(fav))), 200


@recipes_bp.post("/<rid>/favorite")
@login_required
def toggle_favorite(rid):
    user = _current_user()
    if Recipe.alive().filter_by(id=rid).first() is None:
        return jsonify(error="Not found"), 404
    row = RecipeFavorite.query.filter_by(user_id=user.id, recipe_id=rid).first()
    if row:
        db.session.delete(row); fav = False
    else:
        db.session.add(RecipeFavorite(user_id=user.id, recipe_id=rid)); fav = True
    db.session.commit()
    return jsonify(favorited=fav), 200
