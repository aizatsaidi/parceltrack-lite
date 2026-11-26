"""
MODULE 3 - Delivery Update and Admin Dashboard  (owner: Aizat)

Working now (for the progress demo):
  - Admin "Assign Parcels" page with a status summary (dashboard)
  - Rider "My Parcels" page: only parcels assigned to that rider
  - Rider parcel detail page

Security controls already in place:
  SR3.1  Only Admin can open the assign page and assign parcels (checked on the server)
  SR3.2  A rider can only open parcels assigned to them; any other ID returns 403
  SR3.5  Every assignment is written to status_history with who and when
  SR3.6  Forms carry a CSRF token; templates escape recipient data
  SR3.7  The dashboard shows only counts per status, no personal data
         (rider workload and recent activity show staff names, tracking numbers,
         statuses and times only, never recipient details)

Next steps: rider status update with valid order (SR3.3) and
secure proof-of-delivery photo upload (SR3.4).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user

from .. import db
from ..models import Parcel, User, StatusHistory, record_status_change
from ..security import role_required

delivery_bp = Blueprint("delivery", __name__)

STATUSES = ["Registered", "Assigned", "Out for Delivery", "Delivered", "Failed"]


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


@delivery_bp.route("/rider/parcels/<int:parcel_id>")
@role_required("rider")
def rider_parcel_detail(parcel_id):
    parcel = db.session.get(Parcel, parcel_id)
    # The key access-control check: changing the ID in the URL gets 403
    if parcel is None or parcel.assigned_rider_id != current_user.id:
        abort(403)
    return render_template("delivery/rider_parcel_detail.html", parcel=parcel)
