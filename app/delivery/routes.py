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

Next steps: rider status update with valid order (SR3.3) and
secure proof-of-delivery photo upload (SR3.4).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user

from .. import db
from ..models import Parcel, User, record_status_change
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
    return render_template("delivery/assign.html", counts=counts,
                           parcels=waiting, riders=riders)


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
