# M3 · Delivery Update and Admin Dashboard · Aizat

Policies: **P1, P3, P5** · Folder: `app/delivery/`, `app/templates/delivery/` · Tests: `tests/test_m3.py`

## Already working

- Admin assigns Registered parcels to active riders (`/admin/assign`); logged in `status_history`
- Admin dashboard of parcel counts by status on the same page (Admin only, counts only)
- Rider sees only their assigned parcels (`/rider/parcels`); any other parcel ID returns 403

## To do (one item at a time)

1. **Rider status update** on the parcel detail page (POST `/rider/parcels/<id>/status`).
   Allowed changes only:
   - Assigned → Out for Delivery
   - Out for Delivery → Delivered or Failed

   Reject any other value or jump, such as `Delivered` straight from `Assigned` or a made-up
   status like `Lost`, with a generic message. The server must check the parcel is assigned
   to the logged-in rider. Use `record_status_change()` from `app/models.py` so every change
   is logged with user and time (P5). Set `delivered_at` when Delivered.
2. **Proof-of-delivery photo upload**, required for Delivered and Failed:
   - Allow only `.jpg`, `.jpeg` and `.png`. The 5 MB limit is already set (`MAX_CONTENT_LENGTH`).
   - Check the real content: open the file with **Pillow** (add to `requirements.txt`),
     verify it is a JPEG or PNG image, then re-save it (this also removes hidden data).
   - Save it under a random name (`uuid4().hex + ".jpg"`) in `uploads/`, which is outside
     `app/static`, so it can never be run or opened directly.
   - Store the name in the `delivery_photos` table.
3. **View photo route** (`/photos/<photo_id>`): only the assigned rider and Admin can
   see the photo. Use `send_from_directory`; anyone else gets 403.
4. **Show the status history and photo** on the rider's parcel page and an Admin parcel view.
5. **Tests** in `tests/test_m3.py`, at least 6 input types.

## Rubric key controls (criterion 2a)

Rider updates only assigned parcels (server-side check) · only Admin assigns and views the
dashboard · upload checks type, size and real content, renames the file and stores it
outside the web root · status changes logged with user and time · parameterised queries.

## Rubric suggested tests (criterion 3)

| Input | Expected result |
|---|---|
| Upload `shell.php` | Rejected: only JPG or PNG |
| Upload `shell.php.jpg` (a text file renamed) | Rejected: not a real image |
| Upload a 10 MB image | Rejected: file too large (413) |
| Send status `Lost`, or `Delivered` straight from `Assigned` | Rejected; status unchanged |
| Rider updates a parcel assigned to someone else | 403; status unchanged |
| Open `/admin/assign` without Admin login | Redirect to login, or 403 for other roles |

## Things to be ready to explain in the demo

Why the server checks the rider on every request (P1); why the file name alone is not
enough and the content is checked; why uploads are renamed and kept outside the web folder;
how `status_history` gives accountability (P5); why the dashboard shows only counts (P3).
