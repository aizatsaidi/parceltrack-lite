"""
MODULE 3 - Delivery Update and Admin Dashboard  (owner: Aizat)

Working now:
  - Admin "Assign Parcels" page with a status summary (dashboard)
  - Rider "My Parcels" page: only parcels assigned to that rider
  - Rider parcel detail page
  - Rider status update in the correct order (Task 6)
  - Proof-of-delivery photo, required for Delivered and Failed (Task 9)
  - Protected link to view a delivery photo (Task 12)

Security controls already in place:
  SR3.1  Only Admin can open the assign page and assign parcels (checked on the server)
  SR3.2  A rider can only open or update parcels assigned to them; any other ID returns 403
  SR3.3  Status changes only in order: Assigned -> Out for Delivery -> Delivered or Failed;
         any other value, skipped step or backwards step is rejected (ALLOWED_NEXT)
  SR3.4  Delivery photos: only real JPG/PNG under 5 MB, re-saved clean, random name,
         stored outside app/static (checks in uploads.py)
         Photos are only shown through /photos/<id>, and only to the assigned rider,
         the Admin and the seller who owns the parcel (P1, P3)
  SR3.5  Every assignment is written to status_history with who and when
  SR3.6  Forms carry a CSRF token; templates escape recipient data
  SR3.7  The dashboard shows only counts per status, no personal data
         (rider workload and recent activity show staff names, tracking numbers,
         statuses and times only, never recipient details)

Next steps: show status history and photo on parcel pages + Admin parcel view (Task 14).
"""
import re

from flask import (Blueprint, render_template, request, redirect, url_for, flash, abort,
                   current_app, send_from_directory)
from flask_login import current_user

from .. import db
from ..models import Parcel, User, StatusHistory, DeliveryPhoto, record_status_change, utcnow
from ..security import role_required
from .uploads import save_delivery_photo, PhotoRejected

delivery_bp = Blueprint("delivery", __name__)

STATUSES = ["Registered", "Assigned", "Out for Delivery", "Delivered", "Failed"]

# SR3.3: the ONLY status changes a rider may make, in order.
# Anything not listed here (skipping a step, going backwards, a made-up status) is rejected.
ALLOWED_NEXT = {
    "Assigned": ["Out for Delivery"],
    "Out for Delivery": ["Delivered", "Failed"],
}

# SR3.4: these final steps need a proof-of-delivery photo
PHOTO_REQUIRED = {"Delivered", "Failed"}
PHOTO_ERROR = "Please upload a JPG or PNG photo under 5 MB."


@delivery_bp.route("/admin/assign", methods=["GET", "POST"])
@role_required("admin")
def assign():
    if request.method == "POST":
        # Never trust form values: look both records up again on the server
        try:
            parcel_id = int(request.form.get("parcel_id", ""))
            rider_id = int(request.form.get("rider_id", ""))
        except ValueError:
            flash("Please choose a rider.", "danger")
            return redirect(url_for("delivery.assign"))

        parcel = db.session.get(Parcel, parcel_id)
        rider = db.session.get(User, rider_id)

        if parcel is None or parcel.status != "Registered":
            flash("This parcel cannot be assigned.", "danger")
        elif rider is None or rider.role != "rider" or not rider.is_active_account:
            flash("Please choose an active rider.", "danger")
        else:
            parcel.assigned_rider_id = rider.id
            record_status_change(parcel, "Assigned", current_user)
            db.session.commit()
            flash(f"{parcel.tracking_no} assigned to {rider.name}.", "success")
        return redirect(url_for("delivery.assign"))

    # Dashboard: counts only, no personal data
    counts = {s: Parcel.query.filter_by(status=s).count() for s in STATUSES}
    waiting = Parcel.query.filter_by(status="Registered").order_by(Parcel.created_at).all()
    riders = User.query.filter_by(role="rider", is_active_account=True).order_by(User.name).all()

    # Rider workload: how many parcels each active rider is carrying right now
    workload = [
        {"name": r.name,
         "active": Parcel.query.filter(Parcel.assigned_rider_id == r.id,
                                       Parcel.status.in_(["Assigned", "Out for Delivery"])).count(),
         "done": Parcel.query.filter_by(assigned_rider_id=r.id, status="Delivered").count()}
        for r in riders
    ]

    # Recent activity from the audit log (P5): who changed which parcel, and when.
    # Only tracking numbers, statuses, names of staff and times; never recipient details.
    recent = (StatusHistory.query
              .order_by(StatusHistory.changed_at.desc(), StatusHistory.id.desc())
              .limit(5).all())
    names = {u.id: u.name for u in User.query.filter(
        User.id.in_({h.changed_by for h in recent})).all()} if recent else {}
    activity = [{"tracking_no": h.parcel.tracking_no, "old": h.old_status, "new": h.new_status,
                 "by": names.get(h.changed_by, "Unknown"), "when": h.changed_at} for h in recent]

    return render_template("delivery/assign.html", counts=counts, total=sum(counts.values()),
                           parcels=waiting, riders=riders, workload=workload, activity=activity)


@delivery_bp.route("/rider/parcels")
@role_required("rider")
def rider_parcels():
    parcels = (Parcel.query.filter_by(assigned_rider_id=current_user.id)  # own only
               .order_by(Parcel.created_at.desc()).all())
    return render_template("delivery/rider_parcels.html", parcels=parcels)


def own_parcel_or_403(parcel_id):
    """The key access-control check (SR3.2, P1): the parcel must be assigned to
    the logged-in rider. Any other ID, including one that doesn't exist, gets 403,
    so changing the number in the URL never reveals someone else's parcel."""
    parcel = db.session.get(Parcel, parcel_id)
    if parcel is None or parcel.assigned_rider_id != current_user.id:
        # Security event for the log (P5): IDs only, no recipient details
        current_app.logger.warning("Blocked access: rider %s tried parcel %s (%s %s)",
                                   current_user.id, parcel_id, request.method, request.path)
        abort(403)
    return parcel


@delivery_bp.route("/rider/parcels/<int:parcel_id>")
@role_required("rider")
def rider_parcel_detail(parcel_id):
    parcel = own_parcel_or_403(parcel_id)
    next_options = ALLOWED_NEXT.get(parcel.status, [])
    photo = (DeliveryPhoto.query.filter_by(parcel_id=parcel.id)
             .order_by(DeliveryPhoto.id.desc()).first())
    return render_template("delivery/rider_parcel_detail.html", parcel=parcel,
                           next_options=next_options,
                           needs_photo=any(s in PHOTO_REQUIRED for s in next_options),
                           photo=photo)


@delivery_bp.route("/rider/parcels/<int:parcel_id>/status", methods=["POST"])
@role_required("rider")
def update_status(parcel_id):
    """Task 6 (SR3.3): a rider moves their own parcel one step along the route."""
    parcel = own_parcel_or_403(parcel_id)                 # 403 if not this rider's parcel
    new_status = request.form.get("new_status", "").strip()

    # Never trust the form: only the next steps listed in ALLOWED_NEXT are accepted.
    # A made-up value, an empty value, skipping a step or going backwards is rejected.
    if new_status not in ALLOWED_NEXT.get(parcel.status, []):
        # Technical detail goes to the log only (P4); no recipient details in it (P5)
        current_app.logger.warning(
            "Rejected status change: parcel %s from %r to %r by rider %s",
            parcel.id, parcel.status, new_status[:30], current_user.id)
        flash("That status change isn't allowed for this parcel.", "danger")
        return redirect(url_for("delivery.rider_parcel_detail", parcel_id=parcel.id))

    # Task 9 (SR3.4): Delivered and Failed need a photo that passes every check.
    # If anything fails, nothing is saved and the status stays the same.
    if new_status in PHOTO_REQUIRED:
        upload = request.files.get("photo")
        try:
            stored_filename = save_delivery_photo(upload, current_app.config["UPLOAD_FOLDER"])
        except PhotoRejected as reason:
            current_app.logger.warning(
                "Rejected delivery photo: parcel %s by rider %s, file %r: %s",
                parcel.id, current_user.id, (upload.filename if upload else "")[:60], reason)
            flash(PHOTO_ERROR, "danger")
            return redirect(url_for("delivery.rider_parcel_detail", parcel_id=parcel.id))
        db.session.add(DeliveryPhoto(parcel_id=parcel.id, stored_filename=stored_filename,
                                     uploaded_by=current_user.id))

    record_status_change(parcel, new_status, current_user)   # audit log: who and when (P5)
    if new_status == "Delivered":
        parcel.delivered_at = utcnow()                        # used later for the P3 clean-up
    db.session.commit()
    flash(f"{parcel.tracking_no} is now {new_status}.", "success")
    return redirect(url_for("delivery.rider_parcel_detail", parcel_id=parcel.id))


# Only names the server itself created in uploads.py can ever be sent (random hex + .jpg/.png)
SAFE_PHOTO_NAME = re.compile(r"[0-9a-f]{32}\.(jpg|png)")


def can_view_photo(user, parcel):
    """Who may see a delivery photo (P1, P3): it can show the recipient's door or face."""
    if user.role == "admin":
        return True
    if user.role == "rider":
        return parcel.assigned_rider_id == user.id     # the rider who delivered it
    if user.role == "seller":
        return parcel.seller_id == user.id             # the seller who sent it
    return False


@delivery_bp.route("/photos/<int:photo_id>")
@role_required("seller", "rider", "admin")             # not logged in -> sent to the login page
def view_photo(photo_id):
    """Task 12: show one delivery photo, only to people allowed to see it."""
    photo = db.session.get(DeliveryPhoto, photo_id)
    parcel = db.session.get(Parcel, photo.parcel_id) if photo else None

    # Same 403 for "doesn't exist" and "not yours", so IDs can't be guessed
    if parcel is None or not can_view_photo(current_user, parcel):
        current_app.logger.warning("Blocked photo access: user %s (%s) tried photo %s",
                                   current_user.id, current_user.role, photo_id)
        abort(403)

    # The path comes ONLY from the database, never from the URL, and must look like a
    # name we created. "../" tricks can't reach other files.
    if not SAFE_PHOTO_NAME.fullmatch(photo.stored_filename):
        current_app.logger.error("Unsafe stored photo name for photo %s", photo.id)
        abort(404)

    response = send_from_directory(current_app.config["UPLOAD_FOLDER"], photo.stored_filename)
    response.headers["Cache-Control"] = "private, no-store"     # don't keep copies in shared caches
    response.headers["X-Content-Type-Options"] = "nosniff"      # browser must treat it as an image
    return response
