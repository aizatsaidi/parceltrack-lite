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
