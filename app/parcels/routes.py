"""
MODULE 2 - Parcel Registration and Public Tracking  (owner: Member 2)

Working now (for the progress demo):
  - Seller registers a parcel and gets a tracking number
  - Seller views and searches their own parcels
  - Public tracking page (no login)

Security controls already in place:
  SR2.1  Tracking numbers come from a secure random generator (secrets)
  SR2.2  All database queries go through the ORM (parameterised, no SQL injection)
  SR2.3  A seller only ever sees parcels where seller_id = their own id
  SR2.4  The public page shows status, date and time only - no name, phone or address
  SR2.6  Inputs are checked on the server; templates escape all output (XSS)

Next steps: rate-limit the tracking page (SR2.5), better phone validation.
"""
import re
import secrets
import string

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from .. import db
from ..models import Parcel, StatusHistory
from ..security import role_required

parcels_bp = Blueprint("parcels", __name__)

# Letters and digits that are easy to read (no 0/O or 1/I)
TRACKING_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")
PHONE_PATTERN = re.compile(r"^\+?[0-9\- ]{9,15}$")


def new_tracking_number():
    """e.g. RX-7KQ2M9XAP4 : 10 random characters, about 50 bits, not guessable."""
    while True:
        code = "RX-" + "".join(secrets.choice(TRACKING_ALPHABET) for _ in range(10))
        if not Parcel.query.filter_by(tracking_no=code).first():
            return code


@parcels_bp.route("/seller/parcels")
@role_required("seller")
def my_parcels():
    q = request.args.get("q", "").strip()[:50]
    query = Parcel.query.filter_by(seller_id=current_user.id)  # own parcels only
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Parcel.tracking_no.ilike(like),
                                    Parcel.recipient_name.ilike(like)))
    parcels = query.order_by(Parcel.created_at.desc()).all()
    return render_template("parcels/my_parcels.html", parcels=parcels, q=q)


@parcels_bp.route("/seller/parcels/new", methods=["GET", "POST"])
@role_required("seller")
def new_parcel():
    if request.method == "POST":
        name = request.form.get("recipient_name", "").strip()
        phone = request.form.get("recipient_phone", "").strip()
        address = request.form.get("recipient_address", "").strip()
        weight_text = request.form.get("weight_kg", "").strip()

        errors = []
        if not name or len(name) > 100:
            errors.append("Recipient name is required (up to 100 characters).")
        if not PHONE_PATTERN.match(phone):
            errors.append("Phone number should be 9 to 15 digits, e.g. 012-3456789.")
        if not address or len(address) > 255:
            errors.append("Address is required (up to 255 characters).")
        try:
            weight = float(weight_text)
            if not 0 < weight <= 30:
                raise ValueError
        except ValueError:
            errors.append("Weight must be a number between 0 and 30 kg.")
            weight = None

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("parcels/new_parcel.html", form=request.form), 400

        parcel = Parcel(tracking_no=new_tracking_number(), seller_id=current_user.id,
                        recipient_name=name, recipient_phone=phone,
                        recipient_address=address, weight_kg=weight, status="Registered")
        db.session.add(parcel)
        db.session.flush()  # gives the parcel an id
        # First line of the parcel's history (used by the public tracking page)
        db.session.add(StatusHistory(parcel_id=parcel.id, old_status=None,
                                     new_status="Registered", changed_by=current_user.id))
        db.session.commit()
        flash(f"Parcel registered. Tracking number: {parcel.tracking_no}", "success")
        return redirect(url_for("parcels.my_parcels"))

    return render_template("parcels/new_parcel.html", form={})


@parcels_bp.route("/track")
def track():
    """Public page - no login. Shows ONLY status, date and time."""
    tracking_no = request.args.get("tracking_no", "").strip().upper()[:20]
    history = None
    not_found = False
    if tracking_no:
        parcel = Parcel.query.filter_by(tracking_no=tracking_no).first()
        if parcel:
            # Build a safe list: no recipient details leave the server
            history = [{"status": h.new_status, "when": h.changed_at} for h in parcel.history]
        else:
            not_found = True
    return render_template("parcels/track.html", tracking_no=tracking_no,
                           history=history, not_found=not_found)
