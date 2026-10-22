"""
ParcelTrack Lite - app setup (SHARED by the whole group).

This file creates the Flask app, connects the database, and switches on
the security features every module relies on:
  - CSRF protection on every form (Flask-WTF)
  - Login sessions (Flask-Login)
  - Safer session cookies
  - Generic error pages (policy P4: no technical details shown to users)
"""
import os
import logging

from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    # Secrets come from the .env file, never from the source code (policy P4)
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(32)
    # Default: a local SQLite file so the demo runs with no setup.
    # For MySQL, set DATABASE_URL in .env (see .env.example).
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(base_dir, "parceltrack.db")
    )
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

    # Safer session cookies: JavaScript can't read them, and they are not
    # sent from other websites. Set SESSION_COOKIE_SECURE=1 once on HTTPS.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "1"
    app.config["PERMANENT_SESSION_LIFETIME"] = 30 * 60  # 30 minutes

    # Technical errors go to a log file only (policy P4)
    logging.basicConfig(
        filename=os.path.join(base_dir, "parceltrack.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(User, int(user_id))
        # A disabled account is logged out straight away (policy P1)
        if user is None or not user.is_active_account:
            return None
        return user

    # Each module is a separate blueprint (folder) owned by one member
    from .auth.routes import auth_bp          # Module 1
    from .parcels.routes import parcels_bp    # Module 2
    from .delivery.routes import delivery_bp  # Module 3

    app.register_blueprint(auth_bp)
    app.register_blueprint(parcels_bp)
    app.register_blueprint(delivery_bp)

    # Times are stored in UTC; show them in Malaysia time (UTC+8)
    @app.template_filter("myt")
    def to_malaysia_time(value, fmt="%d %b %Y, %H:%M"):
        from datetime import timedelta
        return (value + timedelta(hours=8)).strftime(fmt) if value else ""

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("delivery.assign"))
            if current_user.role == "rider":
                return redirect(url_for("delivery.rider_parcels"))
            return redirect(url_for("parcels.my_parcels"))
        return render_template("home.html")

    # Generic error pages: users never see stack traces or SQL errors
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="You do not have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               message="Page not found."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("error.html", code=413,
                               message="The file is too large."), 413

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Server error")
        return render_template("error.html", code=500,
                               message="Something went wrong. Please try again."), 500

    return app
