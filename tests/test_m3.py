"""
Module 3 (Aizat): security tests for the rider status update (Task 6, SR3.3).
Run with:   python -m pytest tests -v

Demo parcels (from app/seed.py, fake data only):
  RX-DEMO9HN3QX  Assigned          -> Rider Ali
  RX-DEMOB6R2VK  Assigned          -> Rider Siti
  RX-DEMOT5W8LC  Out for Delivery  -> Rider Ali
  RX-DEMOH2Y6RF  Delivered         -> Rider Siti
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ALI = ("ali@rapidexpress.test", "RiderAliDemo#2026")
SITI = ("siti@rapidexpress.test", "RiderSitiDemo#2026")
SELLER = ("seller@shop.test", "SellerDemo#2026")
ADMIN = ("admin@rapidexpress.test", "AdminDemo#2026")


@pytest.fixture
def client():
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file.name
    from app import create_app, db
    from app.seed import seed
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # turned back on in the CSRF test
    with app.app_context():
        seed()
        yield app.test_client(), app
        db.session.remove()
        db.engine.dispose()
    os.environ.pop("DATABASE_URL", None)
    os.unlink(db_file.name)


def login(c, who):
    return c.post("/login", data={"email": who[0], "password": who[1]})


def parcel(tracking_no):
    from app import db
    from app.models import Parcel
    db.session.expire_all()  # always read the latest saved values
    return Parcel.query.filter_by(tracking_no=tracking_no).first()


def history_count(p):
    from app.models import StatusHistory
    return StatusHistory.query.filter_by(parcel_id=p.id).count()


def set_status(c, p, new_status):
    return c.post(f"/rider/parcels/{p.id}/status", data={"new_status": new_status})


# ---------- valid changes ----------

def test_SR3_3_valid_route_is_logged_with_rider_and_time(client):
    c, _ = client
    from app.models import StatusHistory, User
    ali = User.query.filter_by(email=ALI[0]).first()
    p = parcel("RX-DEMO9HN3QX")
    login(c, ALI)

    set_status(c, p, "Out for Delivery")
    assert parcel("RX-DEMO9HN3QX").status == "Out for Delivery"
    set_status(c, p, "Delivered")
    p = parcel("RX-DEMO9HN3QX")
    assert p.status == "Delivered"
    assert p.delivered_at is not None

    last_two = (StatusHistory.query.filter_by(parcel_id=p.id)
                .order_by(StatusHistory.id.desc()).limit(2).all())
    assert [h.new_status for h in last_two] == ["Delivered", "Out for Delivery"]
    assert all(h.changed_by == ali.id and h.changed_at is not None for h in last_two)


def test_SR3_3_out_for_delivery_can_fail(client):
    c, _ = client
    p = parcel("RX-DEMOT5W8LC")
    login(c, ALI)
    set_status(c, p, "Failed")
    assert parcel("RX-DEMOT5W8LC").status == "Failed"


# ---------- invalid values and jumps are rejected ----------

@pytest.mark.parametrize("bad_value", ["Lost", "", "Delivered", "Registered", "assigned", "Out for Delivery<script>"])
def test_SR3_3_invalid_or_skipped_status_rejected(client, bad_value):
    c, _ = client
    p = parcel("RX-DEMO9HN3QX")          # currently Assigned
    before = history_count(p)
    login(c, ALI)
    r = set_status(c, p, bad_value)
    assert r.status_code == 302           # sent back with a generic message
    p = parcel("RX-DEMO9HN3QX")
    assert p.status == "Assigned"         # unchanged
    assert history_count(p) == before     # nothing logged as a change


def test_SR3_3_finished_delivery_cannot_change(client):
    c, _ = client
    p = parcel("RX-DEMOH2Y6RF")          # already Delivered (Siti)
    login(c, SITI)
    set_status(c, p, "Out for Delivery")
    set_status(c, p, "Failed")
    assert parcel("RX-DEMOH2Y6RF").status == "Delivered"


def test_SR3_3_rejection_message_is_generic(client):
    c, _ = client
    p = parcel("RX-DEMO9HN3QX")
    login(c, ALI)
    r = c.post(f"/rider/parcels/{p.id}/status", data={"new_status": "Lost"}, follow_redirects=True)
    assert b"isn&#39;t allowed" in r.data or b"isn't allowed" in r.data
    assert b"Traceback" not in r.data


# ---------- access control ----------

def test_SR3_2_rider_cannot_update_another_riders_parcel(client):
    c, _ = client
    p = parcel("RX-DEMOB6R2VK")          # Siti's parcel
    login(c, ALI)
    r = set_status(c, p, "Out for Delivery")
    assert r.status_code == 403
    assert parcel("RX-DEMOB6R2VK").status == "Assigned"


def test_SR3_2_unknown_parcel_id_is_403(client):
    c, _ = client
    login(c, ALI)
    assert c.post("/rider/parcels/99999/status", data={"new_status": "Out for Delivery"}).status_code == 403


@pytest.mark.parametrize("who", [SELLER, ADMIN])
def test_SR3_1_only_riders_can_update_status(client, who):
    c, _ = client
    p = parcel("RX-DEMO9HN3QX")
    login(c, who)
    assert set_status(c, p, "Out for Delivery").status_code == 403
    assert parcel("RX-DEMO9HN3QX").status == "Assigned"


def test_logged_out_user_is_sent_to_login(client):
    c, _ = client
    p = parcel("RX-DEMO9HN3QX")
    r = set_status(c, p, "Out for Delivery")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert parcel("RX-DEMO9HN3QX").status == "Assigned"


def test_SR3_6_status_update_without_csrf_token_rejected(client):
    c, app = client
    p = parcel("RX-DEMO9HN3QX")
    login(c, ALI)
    app.config["WTF_CSRF_ENABLED"] = True
    r = set_status(c, p, "Out for Delivery")
    assert r.status_code == 400
    assert parcel("RX-DEMO9HN3QX").status == "Assigned"


def test_SR3_6_csrf_page_is_styled_and_logged(client, caplog):
    c, app = client
    p = parcel("RX-DEMO9HN3QX")
    login(c, ALI)
    app.config["WTF_CSRF_ENABLED"] = True
    with caplog.at_level("WARNING"):
        r = set_status(c, p, "Out for Delivery")
    assert r.status_code == 400
    assert b"This form has expired" in r.data   # our own page, not Flask's default
    assert b"CSRF token is missing" not in r.data                # no technical detail shown (P4)
    assert any("CSRF" in m and f"/rider/parcels/{p.id}/status" in m for m in caplog.messages)


# ---------- security events are logged (P5) ----------

def test_P5_blocked_access_is_logged(client, caplog):
    c, _ = client
    p = parcel("RX-DEMOB6R2VK")          # Siti's parcel
    login(c, ALI)
    with caplog.at_level("WARNING"):
        c.get(f"/rider/parcels/{p.id}")
    assert any("Blocked access" in m and f"parcel {p.id}" in m for m in caplog.messages)
    assert not any("Test Recipient" in m for m in caplog.messages)   # no personal data in the log


def test_P5_rejected_status_is_logged(client, caplog):
    c, _ = client
    p = parcel("RX-DEMO9HN3QX")
    login(c, ALI)
    with caplog.at_level("WARNING"):
        set_status(c, p, "Lost")
    assert any("Rejected status change" in m and "'Lost'" in m for m in caplog.messages)


# ---------- the page only offers the allowed next steps ----------

def test_page_offers_only_next_steps(client):
    c, _ = client
    login(c, ALI)
    page = c.get(f"/rider/parcels/{parcel('RX-DEMO9HN3QX').id}").data
    assert b'value="Out for Delivery"' in page
    assert b'value="Delivered"' not in page
    page = c.get(f"/rider/parcels/{parcel('RX-DEMOT5W8LC').id}").data
    assert b'value="Delivered"' in page and b'value="Failed"' in page
