"""
Policy P3 (Task 16): recipient details and delivery photos are removed
12 months after a delivery is finished. Run with:   python -m pytest tests -v

Uses the fake demo data from app/seed.py; dates are moved back in time inside the
test database to make parcels "old".
"""
import os
import shutil
import sys
import tempfile
import uuid
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REMOVED = "[removed]"
OLD = timedelta(days=400)        # more than 12 months ago
RECENT = timedelta(days=30)


@pytest.fixture
def app():
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file.name
    from app import create_app, db
    from app.seed import seed
    application = create_app()
    application.config["TESTING"] = True
    upload_dir = tempfile.mkdtemp()
    application.config["UPLOAD_FOLDER"] = upload_dir
    with application.app_context():
        seed()
        yield application
        db.session.remove()
        db.engine.dispose()
    os.environ.pop("DATABASE_URL", None)
    os.unlink(db_file.name)
    shutil.rmtree(upload_dir, ignore_errors=True)


def parcel(tracking_no):
    from app import db
    from app.models import Parcel
    db.session.expire_all()
    return Parcel.query.filter_by(tracking_no=tracking_no).first()


def finish(app, tracking_no, status, ago, with_photo=True):
    """Make a demo parcel Delivered or Failed `ago` in the past, optionally with a photo file."""
    from app import db
    from app.models import DeliveryPhoto, StatusHistory, utcnow
    p = parcel(tracking_no)
    when = utcnow() - ago
    p.status = status
    p.delivered_at = when if status == "Delivered" else None
    db.session.add(StatusHistory(parcel_id=p.id, old_status="Out for Delivery", new_status=status,
                                 changed_by=p.assigned_rider_id or p.seller_id, changed_at=when))
    name = None
    if with_photo:
        name = uuid.uuid4().hex + ".jpg"
        with open(os.path.join(app.config["UPLOAD_FOLDER"], name), "wb") as f:
            f.write(b"\xff\xd8 fake test photo")
        db.session.add(DeliveryPhoto(parcel_id=p.id, stored_filename=name,
                                     uploaded_by=p.assigned_rider_id or p.seller_id))
    db.session.commit()
    return name


def run(app, *args):
    return app.test_cli_runner().invoke(args=["anonymise-old-parcels", *args])


def is_anonymised(p):
    return (p.recipient_name, p.recipient_phone, p.recipient_address) == (REMOVED, REMOVED, REMOVED)


def photo_exists(app, name):
    return os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], name))


# ---------- the main rule ----------

def test_P3_old_delivered_parcel_is_anonymised_and_new_one_untouched(app):
    old_photo = finish(app, "RX-DEMOT5W8LC", "Delivered", OLD)
    new_photo = finish(app, "RX-DEMO9HN3QX", "Delivered", RECENT)
    result = run(app)
    assert result.exit_code == 0
    assert "Anonymised 1 parcel(s) and deleted 1 photo(s)" in result.output

    old, new = parcel("RX-DEMOT5W8LC"), parcel("RX-DEMO9HN3QX")
    assert is_anonymised(old)
    assert not is_anonymised(new) and new.recipient_name == "Test Recipient C"

    assert not photo_exists(app, old_photo)                       # file deleted from uploads/
    assert photo_exists(app, new_photo)                           # recent photo kept
    from app.models import DeliveryPhoto
    assert DeliveryPhoto.query.filter_by(parcel_id=old.id).count() == 0
    assert DeliveryPhoto.query.filter_by(parcel_id=new.id).count() == 1


def test_P3_old_failed_parcel_is_anonymised_too(app):
    finish(app, "RX-DEMOT5W8LC", "Failed", OLD)
    finish(app, "RX-DEMO9HN3QX", "Failed", RECENT)
    run(app)
    assert is_anonymised(parcel("RX-DEMOT5W8LC"))
    assert not is_anonymised(parcel("RX-DEMO9HN3QX"))


@pytest.mark.parametrize("days,expected", [(364, False), (366, True)])
def test_P3_twelve_month_boundary(app, days, expected):
    finish(app, "RX-DEMOT5W8LC", "Delivered", timedelta(days=days), with_photo=False)
    run(app)
    assert is_anonymised(parcel("RX-DEMOT5W8LC")) is expected


def test_P3_unfinished_parcels_are_never_touched(app):
    """A parcel still on its way keeps its address, however old it is."""
    from app import db
    from app.models import Parcel, utcnow
    for p in Parcel.query.filter(Parcel.status.in_(["Registered", "Assigned", "Out for Delivery"])):
        p.created_at = utcnow() - timedelta(days=1000)
    db.session.commit()
    run(app)
    for tno in ("RX-DEMO7KQ2M9", "RX-DEMO9HN3QX", "RX-DEMOT5W8LC"):
        assert not is_anonymised(parcel(tno))


# ---------- what stays ----------

def test_P3_tracking_status_and_history_are_kept(app):
    from app.models import StatusHistory
    finish(app, "RX-DEMOT5W8LC", "Delivered", OLD)
    p = parcel("RX-DEMOT5W8LC")
    history_before = StatusHistory.query.filter_by(parcel_id=p.id).count()
    run(app)
    p = parcel("RX-DEMOT5W8LC")
    assert p.tracking_no == "RX-DEMOT5W8LC" and p.status == "Delivered" and p.weight_kg == 1.7
    assert StatusHistory.query.filter_by(parcel_id=p.id).count() == history_before


def test_P3_running_again_changes_nothing(app):
    finish(app, "RX-DEMOT5W8LC", "Delivered", OLD)
    run(app)
    assert "Anonymised 0 parcel(s)" in run(app).output


# ---------- safety ----------

def test_P3_dry_run_changes_nothing(app):
    photo = finish(app, "RX-DEMOT5W8LC", "Delivered", OLD)
    result = run(app, "--dry-run")
    assert "Dry run: 1 parcel(s) and 1 photo(s) would be anonymised" in result.output
    assert not is_anonymised(parcel("RX-DEMOT5W8LC"))
    assert photo_exists(app, photo)


def test_P3_as_of_date_for_demos(app):
    finish(app, "RX-DEMOT5W8LC", "Delivered", RECENT, with_photo=False)
    assert "Dry run: 0 parcel(s)" in run(app, "--dry-run").output
    future = (date.today() + timedelta(days=500)).isoformat()
    # In 500 days both delivered demo parcels (this one and Siti's RX-DEMOH2Y6RF) are due
    assert "Dry run: 2 parcel(s)" in run(app, "--dry-run", "--as-of", future).output


def test_P3_bad_date_is_rejected(app):
    result = run(app, "--as-of", "next-year")
    assert result.exit_code != 0 and "YYYY-MM-DD" in result.output


def test_P3_only_real_photo_files_are_deleted(app):
    """A strange name in the database never makes the job delete other files."""
    from app import db
    from app.models import DeliveryPhoto
    finish(app, "RX-DEMOT5W8LC", "Delivered", OLD, with_photo=False)
    keep = os.path.join(app.config["UPLOAD_FOLDER"], "keep-me.txt")
    with open(keep, "w") as f:
        f.write("not a photo")
    p = parcel("RX-DEMOT5W8LC")
    db.session.add(DeliveryPhoto(parcel_id=p.id, stored_filename="keep-me.txt", uploaded_by=p.assigned_rider_id))
    db.session.commit()
    run(app)
    assert os.path.isfile(keep)
    assert is_anonymised(parcel("RX-DEMOT5W8LC"))


def test_P3_log_has_counts_but_no_personal_data(app, caplog):
    finish(app, "RX-DEMOT5W8LC", "Delivered", OLD)
    with caplog.at_level("INFO"):
        run(app)
    text = " ".join(caplog.messages)
    assert "anonymised 1 parcel(s), deleted 1 photo(s)" in text
    for value in ("Test Recipient", "012-000", "Jalan Contoh", "RX-DEMO"):
        assert value not in text


def test_P3_anonymised_parcel_shows_removed_to_admin(app):
    finish(app, "RX-DEMOT5W8LC", "Delivered", OLD)
    run(app)
    from flask import g
    g.pop("_login_user", None)
    c = app.test_client()
    app.config["WTF_CSRF_ENABLED"] = False
    c.post("/login", data={"email": "admin@rapidexpress.test", "password": "AdminDemo#2026"})
    page = c.get(f"/admin/parcels/{parcel('RX-DEMOT5W8LC').id}").data
    assert b"[removed]" in page and b"Test Recipient E" not in page
    assert b"No photo was uploaded" in page
