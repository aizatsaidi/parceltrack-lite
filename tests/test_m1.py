"""Task 4 checks for Argon2 password hashing in Module 1."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def auth_client():
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file.name

    from app import create_app, db
    from app.seed import seed

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        seed()
    yield app.test_client(), app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()

    if previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_database_url
    os.unlink(db_file.name)


def test_seeded_password_uses_argon2id_and_is_verified(auth_client):
    _, app = auth_client
    from app.auth.passwords import verify_password
    from app.models import User

    with app.app_context():
        user = User.query.filter_by(email="seller@shop.test").first()
        assert user.password_hash.startswith("$argon2id$")
        assert "SellerDemo#2026" not in user.password_hash
        assert verify_password(user.password_hash, "SellerDemo#2026")
        assert not verify_password(user.password_hash, "incorrect password")


def test_registration_and_login_use_argon2id(auth_client):
    client, app = auth_client
    password = "NewSellerPassword#2026"
    response = client.post(
        "/register",
        data={"name": "New Seller", "email": "new@shop.test",
              "password": password, "confirm": password},
    )
    assert response.status_code == 302

    from app.models import User

    with app.app_context():
        user = User.query.filter_by(email="new@shop.test").first()
        assert user.password_hash.startswith("$argon2id$")
        assert password not in user.password_hash

    response = client.post("/login", data={"email": "new@shop.test", "password": password})
    assert response.status_code == 302


def test_login_lockout_still_applies_with_argon2id(auth_client):
    client, _ = auth_client
    for _ in range(5):
        response = client.post("/login", data={"email": "seller@shop.test", "password": "wrong-password"})
        assert response.status_code == 401

    response = client.post("/login", data={"email": "seller@shop.test", "password": "SellerDemo#2026"})
    assert response.status_code == 401


def test_only_admin_can_view_and_submit_rider_management(auth_client):
    client, app = auth_client
    from app.models import User

    with app.app_context():
        rider_id = User.query.filter_by(email="ali@rapidexpress.test").first().id

    for email, password in [
        ("seller@shop.test", "SellerDemo#2026"),
        ("ali@rapidexpress.test", "RiderAliDemo#2026"),
    ]:
        client.post("/login", data={"email": email, "password": password})
        assert client.get("/admin/riders").status_code == 403
        response = client.post("/admin/riders", data={
            "name": "Blocked", "email": "blocked@shop.test",
            "temporary_password": "long-enough-password",
        })
        assert response.status_code == 403
        for action in ("disable", "enable"):
            response = client.post(f"/admin/riders/{rider_id}/status", data={"action": action})
            assert response.status_code == 403
        client.post("/logout")


def test_disabled_rider_cannot_log_in_and_actions_are_audited(auth_client):
    client, app = auth_client
    client.post("/login", data={"email": "admin@rapidexpress.test", "password": "AdminDemo#2026"})

    from app import db
    from app.models import LoginEvent, User

    with app.app_context():
        rider = User.query.filter_by(email="ali@rapidexpress.test").first()
        rider_id = rider.id

    response = client.post(f"/admin/riders/{rider_id}/status", data={"action": "disable"})
    assert response.status_code == 302
    with app.app_context():
        assert not db.session.get(User, rider_id).is_active_account

    blocked_client = app.test_client()
    response = blocked_client.post("/login", data={
        "email": "ali@rapidexpress.test", "password": "RiderAliDemo#2026",
    })
    assert response.status_code == 401
    assert b"Invalid email or password" in response.data

    with app.app_context():
        rider = db.session.get(User, rider_id)
        disabled_event = LoginEvent.query.filter_by(
            user_id=rider_id, event="account_disabled",
        ).order_by(LoginEvent.id.desc()).first()
        assert not rider.is_active_account
        assert disabled_event is not None
        assert disabled_event.ip_address is None

    response = client.post(f"/admin/riders/{rider_id}/status", data={"action": "enable"})
    assert response.status_code == 302
    response = blocked_client.post("/login", data={
        "email": "ali@rapidexpress.test", "password": "RiderAliDemo#2026",
    })
    assert response.status_code == 302

    with app.app_context():
        rider = db.session.get(User, rider_id)
        enabled_event = LoginEvent.query.filter_by(
            user_id=rider_id, event="account_enabled",
        ).order_by(LoginEvent.id.desc()).first()
        assert rider.is_active_account
        assert enabled_event is not None
        assert enabled_event.ip_address is None


def test_logged_in_rider_is_logged_out_after_account_is_disabled(auth_client):
    admin_client, app = auth_client
    rider_client = app.test_client()
    rider_client.post("/login", data={
        "email": "ali@rapidexpress.test", "password": "RiderAliDemo#2026",
    })
    admin_client.post("/login", data={
        "email": "admin@rapidexpress.test", "password": "AdminDemo#2026",
    })

    from app.models import User

    with app.app_context():
        rider_id = User.query.filter_by(email="ali@rapidexpress.test").first().id

    response = admin_client.post(
        f"/admin/riders/{rider_id}/status", data={"action": "disable"},
    )
    assert response.status_code == 302

    response = rider_client.get("/rider/parcels")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_admin_creates_rider_and_form_role_is_ignored(auth_client):
    client, app = auth_client
    client.post("/login", data={"email": "admin@rapidexpress.test", "password": "AdminDemo#2026"})

    response = client.get("/admin/riders")
    assert response.status_code == 200
    assert b"Manage riders" in response.data
    assert b"Active" in response.data

    password = "TemporaryRider#2026"
    response = client.post("/admin/riders", data={
        "name": "New Demo Rider", "email": "new-rider@rapidexpress.test",
        "temporary_password": password, "role": "admin",
    })
    assert response.status_code == 302

    from app.models import User

    with app.app_context():
        rider = User.query.filter_by(email="new-rider@rapidexpress.test").first()
        assert rider.role == "rider"
        assert rider.password_hash.startswith("$argon2id$")
        assert password not in rider.password_hash

    client.post("/logout")
    response = client.post("/login", data={
        "email": "new-rider@rapidexpress.test", "password": password,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"My deliveries" in response.data


def test_admin_rider_creation_rejects_short_password_and_duplicate_email(auth_client):
    client, _ = auth_client
    client.post("/login", data={"email": "admin@rapidexpress.test", "password": "AdminDemo#2026"})

    short_password = client.post("/admin/riders", data={
        "name": "New Rider", "email": "new-rider@rapidexpress.test",
        "temporary_password": "short",
    })
    assert short_password.status_code == 400
    assert b"at least 10 characters" in short_password.data

    duplicate = client.post("/admin/riders", data={
        "name": "Different Name", "email": "seller@shop.test",
        "temporary_password": "TemporaryRider#2026",
    })
    assert duplicate.status_code == 400
    assert b"This email cannot be used" in duplicate.data


def test_change_password_validates_current_short_and_confirm_passwords(auth_client):
    client, app = auth_client
    client.post("/login", data={"email": "seller@shop.test", "password": "SellerDemo#2026"})

    page = client.get("/account/password")
    assert page.status_code == 200
    assert b'name="csrf_token"' in page.data

    wrong_current = client.post("/account/password", data={
        "current_password": "wrong-current-password",
        "new_password": "NewSellerPassword#2026",
        "confirm_password": "NewSellerPassword#2026",
    })
    assert wrong_current.status_code == 400
    assert b"Current password is incorrect" in wrong_current.data

    short_password = client.post("/account/password", data={
        "current_password": "SellerDemo#2026",
        "new_password": "short",
        "confirm_password": "short",
    })
    assert short_password.status_code == 400
    assert b"at least 10 characters" in short_password.data

    mismatch = client.post("/account/password", data={
        "current_password": "SellerDemo#2026",
        "new_password": "NewSellerPassword#2026",
        "confirm_password": "DifferentPassword#2026",
    })
    assert mismatch.status_code == 400
    assert b"New passwords do not match" in mismatch.data

    new_password = "NewSellerPassword#2026"
    changed = client.post("/account/password", data={
        "current_password": "SellerDemo#2026",
        "new_password": new_password,
        "confirm_password": new_password,
    })
    assert changed.status_code == 302
    assert client.get("/seller/parcels").status_code == 200

    from app.models import User

    with app.app_context():
        user = User.query.filter_by(email="seller@shop.test").first()
        assert user.password_hash.startswith("$argon2id$")
        assert new_password not in user.password_hash

    old_password_client = app.test_client()
    response = old_password_client.post("/login", data={
        "email": "seller@shop.test", "password": "SellerDemo#2026",
    })
    assert response.status_code == 401

    new_password_client = app.test_client()
    response = new_password_client.post("/login", data={
        "email": "seller@shop.test", "password": new_password,
    })
    assert response.status_code == 302


def test_password_change_requires_login(auth_client):
    client, _ = auth_client
    response = client.get("/account/password")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_wrong_password_change_attempts_trigger_account_lockout(auth_client):
    client, app = auth_client
    client.post("/login", data={"email": "seller@shop.test", "password": "SellerDemo#2026"})

    for attempt in range(5):
        response = client.post("/account/password", data={
            "current_password": "incorrect-current-password",
            "new_password": "NewSellerPassword#2026",
            "confirm_password": "NewSellerPassword#2026",
        })
        assert response.status_code == (401 if attempt == 4 else 400)

    response = client.post("/account/password", data={
        "current_password": "SellerDemo#2026",
        "new_password": "NewSellerPassword#2026",
        "confirm_password": "NewSellerPassword#2026",
    })
    assert response.status_code == 401
    assert b"Invalid email or password" in response.data

    from app.models import User

    with app.app_context():
        user = User.query.filter_by(email="seller@shop.test").first()
        assert user.failed_logins == 5
        assert user.locked_until is not None
