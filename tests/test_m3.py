"""
Module 3 (Aizat): security tests for the rider status update (Task 6, SR3.3)
and the proof-of-delivery photo upload (Task 9, SR3.4).
Run with:   python -m pytest tests -v

Demo parcels (from app/seed.py, fake data only):
  RX-DEMO9HN3QX  Assigned          -> Rider Ali
  RX-DEMOB6R2VK  Assigned          -> Rider Siti
  RX-DEMOT5W8LC  Out for Delivery  -> Rider Ali
  RX-DEMOH2Y6RF  Delivered         -> Rider Siti
"""
import io
import os
import re
import shutil
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
    upload_dir = tempfile.mkdtemp()          # test photos never land in the real uploads/ folder
    app.config["UPLOAD_FOLDER"] = upload_dir
    with app.app_context():
        seed()
        yield app.test_client(), app
        db.session.remove()
        db.engine.dispose()
    os.environ.pop("DATABASE_URL", None)
    os.unlink(db_file.name)
    shutil.rmtree(upload_dir, ignore_errors=True)


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


def set_status(c, p, new_status, photo=None):
    data = {"new_status": new_status}
    if photo is not None:
        data["photo"] = photo             # (file bytes, file name)
    return c.post(f"/rider/parcels/{p.id}/status", data=data, content_type="multipart/form-data")


def image_file(fmt="JPEG", name="proof.jpg", size=(64, 48), **save_options):
    """A small fake photo made in memory with Pillow (no real pictures in the tests)."""
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", size, (20, 140, 120)).save(buffer, fmt, **save_options)
    buffer.seek(0)
    return (buffer, name)


# ---------- valid changes ----------

def test_SR3_3_valid_route_is_logged_with_rider_and_time(client):
    c, _ = client
    from app.models import StatusHistory, User
    ali = User.query.filter_by(email=ALI[0]).first()
    p = parcel("RX-DEMO9HN3QX")
    login(c, ALI)

    set_status(c, p, "Out for Delivery")
    assert parcel("RX-DEMO9HN3QX").status == "Out for Delivery"
    set_status(c, p, "Delivered", photo=image_file())
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
    set_status(c, p, "Failed", photo=image_file())
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


# ---------- Task 9: proof-of-delivery photo (SR3.4) ----------

OUT = "RX-DEMOT5W8LC"   # Ali's parcel that is Out for Delivery
PHOTO_ERROR = b"Please upload a JPG or PNG photo under 5 MB."


def photos_for(p):
    from app.models import DeliveryPhoto
    return DeliveryPhoto.query.filter_by(parcel_id=p.id).all()


def assert_rejected(c, app, photo, status="Delivered"):
    """The upload is refused: generic message, status unchanged, nothing saved."""
    p = parcel(OUT)
    r = c.post(f"/rider/parcels/{p.id}/status", content_type="multipart/form-data",
               data={"new_status": status, **({"photo": photo} if photo else {})},
               follow_redirects=True)
    assert PHOTO_ERROR in r.data
    assert parcel(OUT).status == "Out for Delivery"
    assert photos_for(p) == []
    assert os.listdir(app.config["UPLOAD_FOLDER"]) == []


@pytest.mark.parametrize("fmt,name,saved_ext", [
    ("JPEG", "proof.jpg", ".jpg"),
    ("JPEG", "PROOF.JPEG", ".jpg"),     # capital letters are fine
    ("PNG", "proof.png", ".png"),
])
def test_SR3_4_valid_photo_saved_with_random_name(client, fmt, name, saved_ext):
    c, app = client
    from app.models import User
    ali = User.query.filter_by(email=ALI[0]).first()
    p = parcel(OUT)
    login(c, ALI)
    set_status(c, p, "Delivered", photo=image_file(fmt, name))

    assert parcel(OUT).status == "Delivered"
    rows = photos_for(p)
    assert len(rows) == 1 and rows[0].uploaded_by == ali.id
    stored = rows[0].stored_filename
    assert re.fullmatch(r"[0-9a-f]{32}" + re.escape(saved_ext), stored)   # random, not "proof"
    assert os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], stored))


def test_SR3_4_failed_also_needs_and_saves_photo(client):
    c, _ = client
    p = parcel(OUT)
    login(c, ALI)
    set_status(c, p, "Failed", photo=image_file("PNG", "doorstep.png"))
    assert parcel(OUT).status == "Failed"
    assert len(photos_for(p)) == 1


@pytest.mark.parametrize("status", ["Delivered", "Failed"])
def test_SR3_4_no_photo_rejected(client, status):
    c, app = client
    login(c, ALI)
    assert_rejected(c, app, None, status)
    assert_rejected(c, app, (io.BytesIO(b""), ""), status)        # empty file field


@pytest.mark.parametrize("photo", [
    (io.BytesIO(b"<?php system($_GET['cmd']); ?>"), "shell.php"),          # a script
    (io.BytesIO(b"<?php system($_GET['cmd']); ?>"), "shell.php.jpg"),      # script pretending to be a photo
    (io.BytesIO(b"just some text"), "notes.txt"),
    (io.BytesIO(b"<svg onload=alert(1)>"), "drawing.svg"),
], ids=["shell.php", "shell.php.jpg", "notes.txt", "drawing.svg"])
def test_SR3_4_non_images_rejected(client, photo):
    c, app = client
    login(c, ALI)
    assert_rejected(c, app, photo)


def test_SR3_4_gif_rejected(client):
    c, app = client
    login(c, ALI)
    assert_rejected(c, app, image_file("GIF", "funny.gif"))          # wrong extension
    assert_rejected(c, app, image_file("GIF", "funny.jpg"))          # real GIF renamed to .jpg


def test_SR3_4_extension_must_match_content(client):
    c, app = client
    login(c, ALI)
    assert_rejected(c, app, image_file("PNG", "photo.jpg"))


def test_SR3_4_broken_image_rejected(client):
    c, app = client
    login(c, ALI)
    real = image_file()[0].getvalue()
    assert_rejected(c, app, (io.BytesIO(real[:60]), "cut.jpg"))      # cut off half-way


def test_SR3_4_image_bomb_rejected(client):
    c, app = client
    from PIL import Image
    login(c, ALI)
    buffer = io.BytesIO()
    Image.new("1", (9000, 5000)).save(buffer, "PNG")                # 45 megapixels, tiny file
    buffer.seek(0)
    assert_rejected(c, app, (buffer, "huge.png"))


def test_SR3_4_file_over_5mb_gets_413(client, caplog):
    c, app = client
    p = parcel(OUT)
    login(c, ALI)
    big = io.BytesIO(b"\xff" * (5 * 1024 * 1024 + 1))
    with caplog.at_level("WARNING"):
        r = set_status(c, p, "Delivered", photo=(big, "big.jpg"))
    assert r.status_code == 413
    assert b"under 5 MB" in r.data
    assert any("Blocked upload over 5 MB" in m for m in caplog.messages)
    assert parcel(OUT).status == "Out for Delivery"
    assert photos_for(p) == []


def test_SR3_4_hidden_data_and_appended_code_removed(client):
    c, app = client
    from PIL import Image
    p = parcel(OUT)
    login(c, ALI)
    exif = Image.Exif()
    exif[0x010E] = "SECRET-NOTE"                                    # hidden description field
    photo, _ = image_file(exif=exif.tobytes())
    evil = photo.getvalue() + b"<?php system($_GET['cmd']); ?>"      # code glued on the end
    set_status(c, p, "Delivered", photo=(io.BytesIO(evil), "proof.jpg"))

    assert parcel(OUT).status == "Delivered"                         # still a real photo, so accepted
    saved = open(os.path.join(app.config["UPLOAD_FOLDER"], photos_for(p)[0].stored_filename), "rb").read()
    assert b"<?php" not in saved
    assert b"SECRET-NOTE" not in saved


def test_SR3_4_big_photo_is_shrunk(client):
    c, app = client
    from PIL import Image
    p = parcel(OUT)
    login(c, ALI)
    set_status(c, p, "Delivered", photo=image_file(size=(4000, 3000)))
    with Image.open(os.path.join(app.config["UPLOAD_FOLDER"], photos_for(p)[0].stored_filename)) as img:
        assert max(img.size) <= 1600


def test_SR3_4_uploads_are_not_public(client):
    c, app = client
    p = parcel(OUT)
    login(c, ALI)
    set_status(c, p, "Delivered", photo=image_file())
    stored = photos_for(p)[0].stored_filename
    for url in (f"/static/{stored}", f"/uploads/{stored}", f"/static/../uploads/{stored}"):
        assert c.get(url).status_code == 404
    static = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "app", "static"))
    real_default = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
    assert not real_default.startswith(static)                       # uploads/ is outside app/static


def test_SR3_4_rejected_upload_is_logged(client, caplog):
    c, app = client
    login(c, ALI)
    with caplog.at_level("WARNING"):
        assert_rejected(c, app, (io.BytesIO(b"<?php ?>"), "shell.php"))
    assert any("Rejected delivery photo" in m and "shell.php" in m for m in caplog.messages)


def test_photo_form_only_when_needed(client):
    c, _ = client
    login(c, ALI)
    page = c.get(f"/rider/parcels/{parcel('RX-DEMO9HN3QX').id}").data   # Assigned: no photo yet
    assert b'type="file"' not in page
    page = c.get(f"/rider/parcels/{parcel(OUT).id}").data                # Out for Delivery
    assert b'type="file"' in page and b'enctype="multipart/form-data"' in page
