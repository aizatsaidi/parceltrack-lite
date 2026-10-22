"""
ParcelTrack Lite - database tables (SHARED by the whole group).
These five tables match the ERD on slide 5.
"""
from datetime import datetime, timezone

from flask_login import UserMixin

from . import db


def utcnow():
    """Current time in UTC (stored in the database)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # never the real password
    role = db.Column(db.String(10), nullable=False)            # seller / rider / admin
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)


class Parcel(db.Model):
    __tablename__ = "parcels"
    id = db.Column(db.Integer, primary_key=True)
    tracking_no = db.Column(db.String(20), unique=True, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_rider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    recipient_name = db.Column(db.String(100), nullable=False)
    recipient_phone = db.Column(db.String(20), nullable=False)
    recipient_address = db.Column(db.String(255), nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Registered", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    delivered_at = db.Column(db.DateTime, nullable=True)

    seller = db.relationship("User", foreign_keys=[seller_id])
    rider = db.relationship("User", foreign_keys=[assigned_rider_id])
    history = db.relationship("StatusHistory", backref="parcel",
                              order_by="StatusHistory.changed_at")


class StatusHistory(db.Model):
    __tablename__ = "status_history"
    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.Integer, db.ForeignKey("parcels.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    changed_at = db.Column(db.DateTime, default=utcnow)


class DeliveryPhoto(db.Model):
    __tablename__ = "delivery_photos"
    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.Integer, db.ForeignKey("parcels.id"), nullable=False)
    stored_filename = db.Column(db.String(100), nullable=False)  # random name, not the user's
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=utcnow)


class LoginEvent(db.Model):
    __tablename__ = "login_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    event = db.Column(db.String(30), nullable=False)  # login / failed_login / locked / logout
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)


def record_status_change(parcel, new_status, user):
    """Write one row to status_history (accountability, policy P5)."""
    entry = StatusHistory(parcel_id=parcel.id, old_status=parcel.status,
                          new_status=new_status, changed_by=user.id)
    parcel.status = new_status
    db.session.add(entry)
