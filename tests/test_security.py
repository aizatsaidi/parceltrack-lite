"""
Automatic security checks for the progress demo.
Run with:   python -m pytest tests -v
Each test matches a security requirement from the slides.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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


def login(c, email, password):
    return c.post("/login", data={"email": email, "password": password})


# ---------- Module 1 ----------

def test_SR1_1_password_is_hashed(client):
    c, app = client
    from app.models import User
    u = User.query.filter_by(email="seller@shop.test").first()
    assert "SellerDemo#2026" not in u.password_hash
    assert u.password_hash.startswith(("scrypt:", "pbkdf2:"))


def test_SR1_2_short_password_rejected(client):
    c, _ = client
    r = c.post("/register", data={"name": "X", "email": "x@x.test",
                                  "password": "short", "confirm": "short"})
    assert r.status_code == 400


def test_SR1_3_lock_after_5_failed_logins(client):
    c, _ = client
    for _ in range(5):
        login(c, "seller@shop.test", "wrong-password")
    r = login(c, "seller@shop.test", "SellerDemo#2026")  # right password, but locked
    assert r.status_code == 401


def test_SR1_4_generic_error_message(client):
    c, _ = client
    r1 = login(c, "seller@shop.test", "wrong-password")
    r2 = login(c, "nobody@nowhere.test", "wrong-password")
    assert b"Invalid email or password" in r1.data
    assert b"Invalid email or password" in r2.data


# ---------- Module 2 ----------

def test_SR2_1_tracking_number_is_random(client):
    c, _ = client
    from app.parcels.routes import new_tracking_number
    numbers = {new_tracking_number() for _ in range(200)}
    assert len(numbers) == 200
    assert all(len(n) == 13 for n in numbers)


def test_SR2_2_sql_injection_in_search(client):
    c, _ = client
    login(c, "seller@shop.test", "SellerDemo#2026")
    r = c.get("/seller/parcels", query_string={"q": "' OR '1'='1"})
    assert r.status_code == 200
    assert b"No parcels found" in r.data


def test_SR2_4_public_tracking_hides_personal_data(client):
    c, _ = client
    r = c.get("/track", query_string={"tracking_no": "RX-DEMO7KQ2M9"})
    assert b"Registered" in r.data
    assert b"Test Recipient A" not in r.data
    assert b"012-0000001" not in r.data
    assert b"Jalan Contoh" not in r.data


def test_SR2_6_xss_is_escaped(client):
    c, _ = client
    login(c, "seller@shop.test", "SellerDemo#2026")
    c.post("/seller/parcels/new", data={"recipient_name": "<script>alert(1)</script>",
                                        "recipient_phone": "012-3456789",
                                        "recipient_address": "Test address",
                                        "weight_kg": "1"})
    r = c.get("/seller/parcels")
    assert b"<script>alert(1)</script>" not in r.data
    assert b"&lt;script&gt;" in r.data


# ---------- Module 3 ----------

def test_SR3_1_seller_cannot_open_admin_page(client):
    c, _ = client
    login(c, "seller@shop.test", "SellerDemo#2026")
    assert c.get("/admin/assign").status_code == 403


def test_SR3_2_rider_cannot_open_other_riders_parcel(client):
    c, _ = client
    from app.models import Parcel
    siti_parcel = Parcel.query.filter_by(tracking_no="RX-DEMOB6R2VK").first()
    ali_parcel = Parcel.query.filter_by(tracking_no="RX-DEMO9HN3QX").first()
    login(c, "ali@rapidexpress.test", "RiderAliDemo#2026")
    assert c.get(f"/rider/parcels/{ali_parcel.id}").status_code == 200
    assert c.get(f"/rider/parcels/{siti_parcel.id}").status_code == 403


def test_SR3_5_assignment_is_logged(client):
    c, _ = client
    from app.models import Parcel, User, StatusHistory
    parcel = Parcel.query.filter_by(status="Registered").first()
    rider = User.query.filter_by(email="ali@rapidexpress.test").first()
    login(c, "admin@rapidexpress.test", "AdminDemo#2026")
    c.post("/admin/assign", data={"parcel_id": parcel.id, "rider_id": rider.id})
    last = StatusHistory.query.filter_by(parcel_id=parcel.id).order_by(StatusHistory.id.desc()).first()
    assert last.new_status == "Assigned"


def test_SR3_6_form_without_csrf_token_rejected(client):
    c, app = client
    login(c, "admin@rapidexpress.test", "AdminDemo#2026")
    app.config["WTF_CSRF_ENABLED"] = True
    r = c.post("/admin/assign", data={"parcel_id": 1, "rider_id": 3})
    assert r.status_code == 400
