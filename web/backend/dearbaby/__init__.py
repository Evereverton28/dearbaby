"""
Application factory. Each domain owns its routes in a blueprint; the app object
is assembled here in exactly one place.
"""

from flask import Flask, jsonify
from dearbaby.config import Config
from dearbaby.extensions import db, jwt, cors
from dearbaby.models import User


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # ------------------------------------------------------------------
    # INSTANT REVOCATION.
    #
    # This runs during token validation, before any route guard. It is the
    # difference between "deactivated users are blocked from admin routes"
    # and "deactivated users are logged out everywhere, immediately".
    #
    # Without this, a deactivated account's already-issued token keeps working
    # on every plain @jwt_required() route until it expires. That bug only
    # surfaces if you test the already-issued-token path, not just login.
    # ------------------------------------------------------------------
    @jwt.token_in_blocklist_loader
    def is_revoked(jwt_header, jwt_payload):
        user = db.session.get(User, jwt_payload.get("sub"))
        return user is None or not user.is_active

    @jwt.revoked_token_loader
    def revoked_response(jwt_header, jwt_payload):
        return jsonify(error="Session revoked. Please sign in again."), 401

    @jwt.expired_token_loader
    def expired_response(jwt_header, jwt_payload):
        return jsonify(error="Session expired. Please sign in again."), 401

    @jwt.unauthorized_loader
    def missing_token_response(reason):
        return jsonify(error="Authentication required"), 401

    @jwt.invalid_token_loader
    def invalid_token_response(reason):
        return jsonify(error="Invalid token"), 401

    # ---- blueprints: one module per domain ---------------------------
    from dearbaby.auth.routes import auth_bp
    from dearbaby.admin.routes import admin_bp
    from dearbaby.analytics.routes import analytics_bp
    from dearbaby.children.routes import children_bp
    from dearbaby.pregnancy.routes import pregnancy_bp
    from dearbaby.memories.routes import memories_bp
    from dearbaby.media.routes import media_bp
    from dearbaby.community.routes import community_bp
    from dearbaby.recipes.routes import recipes_bp
    from dearbaby.notifications.routes import notifications_bp
    from dearbaby.billing.routes import billing_bp
    from dearbaby.settings.routes import settings_bp
    from dearbaby.demo.routes import demo_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(analytics_bp, url_prefix="/api")
    app.register_blueprint(children_bp, url_prefix="/api/children")
    app.register_blueprint(pregnancy_bp, url_prefix="/api/pregnancy")
    app.register_blueprint(memories_bp, url_prefix="/api/memories")
    app.register_blueprint(media_bp, url_prefix="/api/media")
    app.register_blueprint(community_bp, url_prefix="/api/community")
    app.register_blueprint(recipes_bp, url_prefix="/api/recipes")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(billing_bp, url_prefix="/api/billing")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(demo_bp, url_prefix="/api/demo")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="DearBaby API")

    with app.app_context():
        db.create_all()

    return app
