"""
MODULE 3 - Delivery Update and Admin Dashboard  (owner: Aizat)

Working now:
  - Admin "Assign Parcels" page with a status summary (dashboard)
  - Rider "My Parcels" page: only parcels assigned to that rider
  - Rider parcel detail page
  - Rider status update in the correct order (Task 6)

Security controls already in place:
  SR3.1  Only Admin can open the assign page and assign parcels (checked on the server)
  SR3.2  A rider can only open or update parcels assigned to them; any other ID returns 403
  SR3.3  Status changes only in order: Assigned -> Out for Delivery -> Delivered or Failed;
         any other value, skipped step or backwards step is rejected (ALLOWED_NEXT)
  SR3.5  Every assignment is written to status_history with who and when
  SR3.6  Forms carry a CSRF token; templates escape recipient data
  SR3.7  The dashboard shows only counts per status, no personal data
         (rider workload and recent activity show staff names, tracking numbers,
         statuses and times only, never recipient details)

Next steps: secure proof-of-delivery photo upload (SR3.4, Task 9).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import current_user

from .. import db
from ..models import Parcel, User, StatusHistory, record_status_change, utcnow
from ..security import role_required

delivery_bp = Blueprint("delivery", __name__)

STATUSES = ["Registered", "Assigned", "Out for Delivery", "Delivered", "Failed"]

# SR3.3: the ONLY status changes a rider may make, in order.
# Anything not listed here (skipping a step, going backwards, a made-up status) is rejected.
ALLOWED_NEXT = {
    "Assigned": ["Out for Delivery"],
    "Out for Delivery": ["Delivered", "Failed"],
}


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
    return render_template("delivery/rider_parcel_detail.html", parcel=parcel,
                           next_options=ALLOWED_NEXT.get(parcel.status, []))


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

    record_status_change(parcel, new_status, current_user)   # audit log: who and when (P5)
    if new_status == "Delivered":
        parcel.delivered_at = utcnow()                        # used later for the P3 clean-up
    db.session.commit()
    flash(f"{parcel.tracking_no} is now {new_status}.", "success")
    return redirect(url_for("delivery.rider_parcel_detail", parcel_id=parcel.id))
