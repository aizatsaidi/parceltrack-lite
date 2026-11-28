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


def test_21st_tracking_lookup_from_same_ip_gets_generic_429(client):
    c, app = client
    app.config["RATELIMIT_TEST_ENABLED"] = True

    for _ in range(20):
        response = c.get("/track", query_string={"tracking_no": "RX-UNKNOWN123"})
        assert response.status_code == 200

    response = c.get("/track", query_string={"tracking_no": "RX-UNKNOWN123"})

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
