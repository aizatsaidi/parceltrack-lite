"""
Policy P3 - remove personal data we no longer need  (owner: Aizat, Task 16, group task)

A parcel's recipient name, phone and address are needed to deliver it. Twelve
months after the delivery is finished they are not needed any more, so this
job removes them:

  - recipient name, phone and address become "[removed]"
  - the proof-of-delivery photo files are deleted from uploads/ (a photo can show
    a person's face or front door) and their database rows are removed

What stays: the tracking number, weight, status, dates and the status_history
audit log (P5). None of these identify the recipient, so the dashboard counts and
the history still add up.

"Finished" means Delivered (delivered_at) or Failed (the time it was marked Failed).

Run it every day on the server (see docs/DEPLOYMENT.md):
    flask --app app anonymise-old-parcels
Try it safely first:
    flask --app app anonymise-old-parcels --dry-run
    flask --app app anonymise-old-parcels --dry-run --as-of 2028-01-01
On Windows, put "python -m" in front:  python -m flask --app app anonymise-old-parcels --dry-run
"""
import os
import re
from datetime import datetime, timedelta

import click
from flask import current_app

from . import db
from .models import Parcel, StatusHistory, DeliveryPhoto, utcnow

RETENTION_DAYS = 365
REMOVED = "[removed]"
SAFE_PHOTO_NAME = re.compile(r"[0-9a-f]{32}\.(jpg|png)")   # only names uploads.py creates


def parcels_due(now=None):
    """Finished parcels older than 12 months that still hold personal data."""
    cutoff = (now or utcnow()) - timedelta(days=RETENTION_DAYS)
    not_done_yet = Parcel.recipient_name != REMOVED

    delivered = Parcel.query.filter(Parcel.status == "Delivered",
                                    Parcel.delivered_at.isnot(None),
                                    Parcel.delivered_at < cutoff, not_done_yet)
    failed_long_ago = db.session.query(StatusHistory.parcel_id).filter(
        StatusHistory.new_status == "Failed", StatusHistory.changed_at < cutoff)
    failed = Parcel.query.filter(Parcel.status == "Failed",
                                 Parcel.id.in_(failed_long_ago), not_done_yet)
    return {p.id: p for p in delivered.all() + failed.all()}.values()


def anonymise_old_parcels(now=None, dry_run=False):
    """Anonymise every parcel that is due. Returns (parcels, photos) counts."""
    parcels = list(parcels_due(now))
    photos = DeliveryPhoto.query.filter(
        DeliveryPhoto.parcel_id.in_([p.id for p in parcels])).all() if parcels else []
    if dry_run:
        return len(parcels), len(photos)

    folder = current_app.config["UPLOAD_FOLDER"]
    for photo in photos:
        if SAFE_PHOTO_NAME.fullmatch(photo.stored_filename):          # never delete anything else
            path = os.path.join(folder, photo.stored_filename)
            if os.path.isfile(path):
                os.remove(path)
        db.session.delete(photo)
    for parcel in parcels:
        parcel.recipient_name = REMOVED
        parcel.recipient_phone = REMOVED
        parcel.recipient_address = REMOVED
    db.session.commit()

    # Counts only: no names, phones, addresses or tracking numbers in the log (P5, P3)
    current_app.logger.info("P3 clean-up: anonymised %d parcel(s), deleted %d photo(s)",
                            len(parcels), len(photos))
    return len(parcels), len(photos)


def register_commands(app):
    @app.cli.command("anonymise-old-parcels")
    @click.option("--dry-run", is_flag=True, help="Only count what would be removed; change nothing.")
    @click.option("--as-of", "as_of", metavar="YYYY-MM-DD",
                  help="Pretend today is this date (for testing and demos).")
    def anonymise_old_parcels_command(dry_run, as_of):
        """Remove recipient details and photos 12 months after delivery (policy P3)."""
        now = None
        if as_of:
            try:
                now = datetime.strptime(as_of, "%Y-%m-%d")
            except ValueError:
                raise click.BadParameter("use the format YYYY-MM-DD", param_hint="--as-of")
        parcels, photos = anonymise_old_parcels(now=now, dry_run=dry_run)
        if dry_run:
            click.echo(f"Dry run: {parcels} parcel(s) and {photos} photo(s) would be anonymised. Nothing changed.")
        else:
            click.echo(f"Anonymised {parcels} parcel(s) and deleted {photos} photo(s).")
