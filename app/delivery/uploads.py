"""
MODULE 3 - Secure proof-of-delivery photo upload  (owner: Aizat, Task 9, SR3.4)

Threat: malicious file upload. An attacker could try to upload a script
(shell.php), hide one inside a fake picture (shell.php.jpg), or send a huge
or broken image to crash the server. Every upload goes through these checks,
in this order, and is only saved if ALL of them pass:

  1. Extension must be .jpg, .jpeg or .png (any capital letters).
  2. Size: Flask refuses anything over 5 MB before we even see it
     (MAX_CONTENT_LENGTH in app/__init__.py returns 413).
  3. Real content: Pillow must be able to read it as a real JPEG or PNG,
     and the real format must match the extension.
  4. Re-save: we draw a brand-new picture from the pixels only. Hidden data
     (location/EXIF, comments) and anything glued onto the end of the file
     are thrown away.
  5. Random name (uuid4) chosen by the server, saved in uploads/, which is
     outside app/static, so the file can never be opened or run by a URL.
"""
import io
import os
import uuid

from PIL import Image, ImageOps

# Extension -> the real format the content must have
ALLOWED = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}
SAVED_EXTENSION = {"JPEG": ".jpg", "PNG": ".png"}

MAX_PIXELS = 40_000_000   # about 40 megapixels; stops "image bombs" that eat memory
MAX_SIDE = 1600           # big photos are shrunk; plenty for proof of delivery


class PhotoRejected(Exception):
    """The upload failed a check. The message is for the log only, never the user."""


def save_delivery_photo(file, upload_folder):
    """Check an uploaded photo and save a clean copy.
    Returns the new random file name, or raises PhotoRejected."""
    if file is None or not file.filename:
        raise PhotoRejected("no file attached")

    # 1. Extension (the user's file name is only looked at, never used to save)
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED:
        raise PhotoRejected(f"extension {extension!r} not allowed")

    data = file.read()
    if not data:
        raise PhotoRejected("empty file")

    # 3. Real content
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()                               # is the file structure valid?
        image = Image.open(io.BytesIO(data))             # verify() can't be reused, open again
        real_format = image.format
        if real_format != ALLOWED[extension]:
            raise PhotoRejected(f"content is {real_format}, extension is {extension}")
        if image.width * image.height > MAX_PIXELS:
            raise PhotoRejected(f"too many pixels ({image.width}x{image.height})")

        # 4. Re-save from pixels only
        image = ImageOps.exif_transpose(image)           # keep the photo the right way up
        image.thumbnail((MAX_SIDE, MAX_SIDE))
        if real_format == "JPEG":
            image = image.convert("RGB")
        elif image.mode not in ("RGB", "RGBA", "L", "LA"):
            image = image.convert("RGBA")
        clean = Image.new(image.mode, image.size)
        clean.paste(image)                               # pixels only, no metadata
    except PhotoRejected:
        raise
    except Exception as error:                           # broken, fake or unsupported file
        raise PhotoRejected(f"not a valid image ({type(error).__name__})")

    # 5. Random name chosen by the server, saved outside app/static
    os.makedirs(upload_folder, exist_ok=True)
    stored_filename = uuid.uuid4().hex + SAVED_EXTENSION[real_format]
    path = os.path.join(upload_folder, stored_filename)
    if real_format == "JPEG":
        clean.save(path, "JPEG", quality=85)
    else:
        clean.save(path, "PNG", optimize=True)
    return stored_filename
