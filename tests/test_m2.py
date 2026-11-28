"""Task 5: public tracking lookups are rate-limited by client IP."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def client():
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file.name

    from app import create_app, db
    from app.seed import seed

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["RATELIMIT_TEST_ENABLED"] = False
    with app.app_context():
        seed()

    try:
        yield app.test_client(), app
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        os.unlink(db_file.name)


def test_public_tracking_works_normally(client):
    c, _ = client

    response = c.get("/track", query_string={"tracking_no": "RX-DEMO7KQ2M9"})

    assert response.status_code == 200
    assert b"Registered" in response.data


def test_only_tracking_lookups_count_toward_limit(client):
    c, _ = client

    for _ in range(20):
        response = c.get("/track", query_string={"tracking_no": "RX-UNKNOWN123"})
        assert response.status_code == 200

    # Loading the public home page is not a tracking lookup and has no route limit.
    assert c.get("/").status_code == 200


def test_25_tracking_lookups_in_one_minute_get_429_after_limit(client):
    c, app = client
    app.config["RATELIMIT_TEST_ENABLED"] = True

    for attempt in range(25):
        response = c.get("/track", query_string={"tracking_no": "RX-UNKNOWN123"})
        if attempt < 20:
            assert response.status_code == 200
        else:
            assert response.status_code == 429
            assert b"Too many requests, please try again later." in response.data


def login(c, email, password):
    return c.post("/login", data={"email": email, "password": password})


def test_seller_can_view_own_parcel_and_status_history(client):
    c, app = client
    from app.models import Parcel

    login(c, "seller@shop.test", "SellerDemo#2026")
    with app.app_context():
        parcel = Parcel.query.filter_by(tracking_no="RX-DEMO7KQ2M9").first()
        parcel_id = parcel.id

    response = c.get(f"/seller/parcels/{parcel_id}")

    assert response.status_code == 200
    assert b"Test Recipient A" in response.data
    assert b"012-0000001" in response.data
    assert b"Registered" in response.data


def test_seller_status_history_is_chronological_when_timestamps_tie(client):
    c, app = client
    from app.models import Parcel

    login(c, "seller@shop.test", "SellerDemo#2026")
    with app.app_context():
        parcel_id = Parcel.query.filter_by(tracking_no="RX-DEMOH2Y6RF").first().id

    response = c.get(f"/seller/parcels/{parcel_id}")
    assert response.status_code == 200

    timeline = response.data.split(b'<ol class="route">', 1)[1].split(b"</ol>", 1)[0]
    statuses = [b"Registered", b"Assigned", b"Out for Delivery", b"Delivered"]

    assert [timeline.index(status) for status in statuses] == sorted(
        timeline.index(status) for status in statuses
    )


def test_my_parcels_links_to_detail_page(client):
    c, app = client
    from app.models import Parcel

    login(c, "seller@shop.test", "SellerDemo#2026")
    with app.app_context():
        parcel = Parcel.query.filter_by(tracking_no="RX-DEMO7KQ2M9").first()
        parcel_id = parcel.id

    response = c.get("/seller/parcels")

    assert response.status_code == 200
    assert f'href="/seller/parcels/{parcel_id}"'.encode() in response.data


def test_other_seller_and_unknown_parcel_ids_both_return_403(client):
    c, app = client
    from app import db
    from app.auth.passwords import hash_password
    from app.models import Parcel, User

    with app.app_context():
        other_seller = User(name="Second Test Seller", email="second-seller@shop.test",
                            role="seller", password_hash=hash_password("TestSeller#2026"))
        db.session.add(other_seller)
        db.session.flush()
        other_parcel = Parcel(
            tracking_no="RX-SECOND1234", seller_id=other_seller.id,
            recipient_name="Other Test Recipient", recipient_phone="012-0000099",
            recipient_address="99 Test Road", weight_kg=1.0,
        )
        db.session.add(other_parcel)
        db.session.commit()
        other_parcel_id = other_parcel.id

    login(c, "seller@shop.test", "SellerDemo#2026")

    assert c.get(f"/seller/parcels/{other_parcel_id}").status_code == 403
    assert c.get("/seller/parcels/999999").status_code == 403


@pytest.mark.parametrize("email,password", [
    ("ali@rapidexpress.test", "RiderAliDemo#2026"),
    ("admin@rapidexpress.test", "AdminDemo#2026"),
])
def test_rider_and_admin_cannot_open_seller_parcel_detail(client, email, password):
    c, app = client
    from app.models import Parcel

    with app.app_context():
        parcel_id = Parcel.query.filter_by(tracking_no="RX-DEMO7KQ2M9").first().id

    login(c, email, password)

    assert c.get(f"/seller/parcels/{parcel_id}").status_code == 403


@pytest.mark.parametrize(("field", "value", "error", "error_id"), [
    ("recipient_phone", "abc", "Enter a valid phone number with 9 to 15 digits.", "recipient-phone-error"),
    ("recipient_phone", "---------", "Enter a valid phone number with 9 to 15 digits.", "recipient-phone-error"),
    ("weight_kg", "-2", "Enter a valid weight greater than 0 and no more than 30 kg.", "weight-error"),
    ("weight_kg", "100", "Enter a valid weight greater than 0 and no more than 30 kg.", "weight-error"),
    ("weight_kg", "nan", "Enter a valid weight greater than 0 and no more than 30 kg.", "weight-error"),
    ("recipient_address", "", "Enter a delivery address.", "recipient-address-error"),
    ("recipient_address", "   ", "Enter a delivery address.", "recipient-address-error"),
    ("recipient_address", "A" * 256, "Address must be 255 characters or fewer.", "recipient-address-error"),
    ("recipient_name", "   ", "Enter a recipient name.", "recipient-name-error"),
    ("recipient_name", "N" * 101, "Recipient name must be 100 characters or fewer.", "recipient-name-error"),
])
def test_registration_validation_shows_field_error_and_keeps_input(
    client, field, value, error, error_id
):
    c, app = client
    login(c, "seller@shop.test", "SellerDemo#2026")
    from app.models import Parcel

    with app.app_context():
        parcel_count_before = Parcel.query.count()
    form = {
        "recipient_name": "Test Recipient",
        "recipient_phone": "012-3456789",
        "recipient_address": "12 Test Road",
        "weight_kg": "1.25",
    }
    form[field] = value

    response = c.post("/seller/parcels/new", data=form)
    body = response.data

    assert response.status_code == 400
    assert error.encode() in body
    assert f'id="{error_id}" role="alert"'.encode() in body
    assert b"Traceback" not in body
    assert b"ValueError" not in body
    with app.app_context():
        assert Parcel.query.count() == parcel_count_before
    # Valid values and the rejected value are re-rendered safely in the form.
    for name in ("recipient_name", "recipient_phone", "recipient_address", "weight_kg"):
        if name != field and form[name].strip():
            assert form[name].strip().encode() in body
    if value.strip():
        assert value.strip().encode() in body


def test_registration_trims_values_before_saving(client):
    c, app = client
    from app.models import Parcel

    login(c, "seller@shop.test", "SellerDemo#2026")
    response = c.post("/seller/parcels/new", data={
        "recipient_name": "  Trimmed Recipient  ",
        "recipient_phone": " 012-3456789 ",
        "recipient_address": "  12 Trim Road  ",
        "weight_kg": " 1.25 ",
    })

    assert response.status_code == 302
    with app.app_context():
        parcel = Parcel.query.filter_by(recipient_name="Trimmed Recipient").first()
        assert parcel is not None
        assert parcel.recipient_phone == "012-3456789"
        assert parcel.recipient_address == "12 Trim Road"
        assert parcel.weight_kg == 1.25


def test_sql_injection_in_seller_parcel_search_stays_scoped_to_owner(client):
    c, app = client
    from app import db
    from app.auth.passwords import hash_password
    from app.models import Parcel, User

    with app.app_context():
        other_seller = User(
            name="Second Test Seller", email="injection-seller@shop.test",
            role="seller", password_hash=hash_password("TestSeller#2026"),
        )
        db.session.add(other_seller)
        db.session.flush()
        db.session.add(Parcel(
            tracking_no="RX-PRIVATE1234", seller_id=other_seller.id,
            recipient_name="Private Search Recipient", recipient_phone="012-1234567",
            recipient_address="99 Test Road", weight_kg=1.0,
        ))
        db.session.commit()

    login(c, "seller@shop.test", "SellerDemo#2026")
    response = c.get("/seller/parcels", query_string={"q": "' OR '1'='1"})

    assert response.status_code == 200
    assert b"No parcels found." in response.data
    assert b"Private Search Recipient" not in response.data
    assert b"Traceback" not in response.data
    assert b"OperationalError" not in response.data


def test_script_in_address_is_escaped_on_seller_parcel_detail(client):
    c, app = client
    from app.models import Parcel

    login(c, "seller@shop.test", "SellerDemo#2026")
    response = c.post("/seller/parcels/new", data={
        "recipient_name": "XSS Test Recipient",
        "recipient_phone": "012-3456789",
        "recipient_address": "<script>alert(1)</script>",
        "weight_kg": "1.25",
    })
    assert response.status_code == 302

    with app.app_context():
        parcel_id = Parcel.query.filter_by(recipient_name="XSS Test Recipient").first().id

    detail = c.get(f"/seller/parcels/{parcel_id}")

    assert detail.status_code == 200
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in detail.data
    assert b"<script>alert(1)</script>" not in detail.data


def test_unknown_or_sequential_tracking_number_returns_generic_not_found(client):
    c, _ = client

    response = c.get("/track", query_string={"tracking_no": "RX-DEMO000000"})

    assert response.status_code == 200
    assert b"No parcel has that tracking number." in response.data
    assert b"Test Recipient" not in response.data
    assert b"012-" not in response.data
    assert b"Jalan Contoh" not in response.data


def test_public_tracking_never_shows_recipient_personal_data(client):
    c, _ = client

    response = c.get("/track", query_string={"tracking_no": "RX-DEMO7KQ2M9"})

    assert response.status_code == 200
    assert b"Registered" in response.data
    assert b"Test Recipient A" not in response.data
    assert b"012-0000001" not in response.data
    assert b"1 Jalan Contoh" not in response.data
