"""
MODULE 1 - Login and User Management  (owner: Aqil)

Working now (for the progress demo):
  - Login and logout for Seller, Rider and Admin
  - Seller self-registration

Security controls already in place:
  SR1.1  Passwords stored only as salted Argon2id hashes
  SR1.2  Passwords must be at least 10 characters (checked on the server)
  SR1.3  Account locked for 15 minutes after 5 failed logins
  SR1.4  One generic error message: "Invalid email or password"
  SR1.5  Session cleared at login; cookies are HttpOnly (see app/__init__.py)
  SR1.6  Disabled accounts cannot log in
  SR1.7  Logins and failed logins are logged, never the password

Other Module 1 improvements are tracked in docs/tasks/M1-aqil.md.
"""
from datetime import timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from .. import db
from ..models import User, LoginEvent, utcnow
from ..security import role_required
from .passwords import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
MIN_PASSWORD_LENGTH = 10
GENERIC_LOGIN_ERROR = "Invalid email or password."


def log_event(user, event):
    db.session.add(LoginEvent(user_id=user.id if user else None,
                              event=event, ip_address=request.remote_addr))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()  # ORM = parameterised query

        # Locked account: same generic message, so attackers learn nothing
        if user and user.locked_until and user.locked_until > utcnow():
            log_event(user, "login_while_locked")
            db.session.commit()
            flash(GENERIC_LOGIN_ERROR, "danger")
            return render_template("auth/login.html"), 401

        if user and user.is_active_account and verify_password(user.password_hash, password):
            user.failed_logins = 0
            user.locked_until = None
            log_event(user, "login")
            db.session.commit()
            session.clear()  # start a fresh session at login
            login_user(user)
            session.permanent = True  # idle timeout from PERMANENT_SESSION_LIFETIME
            return redirect(url_for("home"))

        # Wrong email or password
        if user:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED_LOGINS:
                user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
                log_event(user, "account_locked")
            else:
                log_event(user, "failed_login")
        else:
            log_event(None, "failed_login_unknown_email")
        db.session.commit()
        flash(GENERIC_LOGIN_ERROR, "danger")
        return render_template("auth/login.html"), 401

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Sellers register themselves. Riders are created by Admin."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        errors = []
        if not name or len(name) > 100:
            errors.append("Please enter your name (up to 100 characters).")
        if "@" not in email or len(email) > 120:
            errors.append("Please enter a valid email address.")
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(email=email).first():
            errors.append("This email cannot be used. Please try another.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", name=name, email=email), 400

        user = User(name=name, email=email, role="seller",
                    password_hash=hash_password(password))
        db.session.add(user)
        db.session.commit()
        flash("Account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    """Let a signed-in user change their password after proving the current one."""
    user = current_user
    if request.method == "POST":
        if user.locked_until and user.locked_until > utcnow():
            log_event(user, "login_while_locked")
            db.session.commit()
            flash(GENERIC_LOGIN_ERROR, "danger")
            return render_template("auth/change_password.html"), 401

        current_password = request.form.get("current_password", "")
        if not verify_password(user.password_hash, current_password):
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED_LOGINS:
                user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
                log_event(user, "account_locked")
            else:
                log_event(user, "failed_password_change")
            db.session.commit()
            flash("Current password is incorrect.", "danger")
            status = 401 if user.locked_until and user.locked_until > utcnow() else 400
            return render_template("auth/change_password.html"), status

        # A verified current password resets failed attempts as a successful login does.
        user.failed_logins = 0
        user.locked_until = None
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            db.session.commit()
            flash(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return render_template("auth/change_password.html"), 400
        if new_password != confirm_password:
            db.session.commit()
            flash("New passwords do not match.", "danger")
            return render_template("auth/change_password.html"), 400

        user.password_hash = hash_password(new_password)
        log_event(user, "password_changed")
        db.session.commit()
        session.clear()
        login_user(user)
        session.permanent = True
        flash("Your password has been changed.", "success")
        return redirect(url_for("home"))

    return render_template("auth/change_password.html")


@auth_bp.route("/admin/riders", methods=["GET", "POST"])
@role_required("admin")
def admin_riders():
    """Let Admin create rider accounts and review their account state."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        temporary_password = request.form.get("temporary_password", "")

        errors = []
        if not name or len(name) > 100:
            errors.append("Please enter the rider's name (up to 100 characters).")
        if "@" not in email or len(email) > 120:
            errors.append("Please enter a valid email address.")
        if len(temporary_password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Temporary password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if User.query.filter_by(email=email).first():
            errors.append("This email cannot be used. Please try another.")

        if errors:
            for error in errors:
                flash(error, "danger")
            riders = User.query.filter_by(role="rider").order_by(User.name).all()
            return render_template("auth/riders.html", riders=riders,
                                   name=name, email=email), 400

        rider = User(name=name, email=email, role="rider",
                     password_hash=hash_password(temporary_password))
        db.session.add(rider)
        db.session.commit()
        flash("Rider account created.", "success")
        return redirect(url_for("auth.admin_riders"))

    riders = User.query.filter_by(role="rider").order_by(User.name).all()
    return render_template("auth/riders.html", riders=riders)


@auth_bp.route("/admin/riders/<int:rider_id>/status", methods=["POST"])
@role_required("admin")
def set_rider_status(rider_id):
    """Enable or disable a rider and record the change without an IP address."""
    rider = db.session.get(User, rider_id)
    if rider is None or rider.role != "rider":
        abort(404)

    action = request.form.get("action", "")
    if action not in {"disable", "enable"}:
        flash("Could not update this rider account.", "danger")
        return redirect(url_for("auth.admin_riders"))

    should_be_active = action == "enable"
    if rider.is_active_account != should_be_active:
        rider.is_active_account = should_be_active
        db.session.add(LoginEvent(
            user_id=rider.id,
            event="account_enabled" if should_be_active else "account_disabled",
            ip_address=None,
        ))
        db.session.commit()
        flash("Rider account enabled." if should_be_active else "Rider account disabled.", "success")
    else:
        flash("Rider account is already enabled." if should_be_active else "Rider account is already disabled.", "info")

    return redirect(url_for("auth.admin_riders"))


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_event(current_user, "logout")
    db.session.commit()
    logout_user()
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("auth.login"))
