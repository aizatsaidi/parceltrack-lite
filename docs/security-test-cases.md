# Module 1 security test cases

Verified with `python -m pytest tests -q`: **150 passed** in the latest full-suite run.

| Input | Expected result | Actual result |
|---|---|---|
| `' OR '1'='1' -- ` in the login email field | Login fails with the generic error; no user is authenticated. | Pass: HTTP 401 with “Invalid email or password.” (`test_sql_injection_email_gets_generic_login_error`) |
| A password shorter than 10 characters at registration or password change | Reject the form and explain the minimum length. | Pass: both forms return HTTP 400 with the minimum-length message (`test_short_registration_password_is_rejected`, `test_change_password_validates_current_short_and_confirm_passwords`). |
| Five incorrect login passwords followed by the correct password | Lock the account for 15 minutes; the correct password is refused during the lockout. | Pass: the stored lockout is about 15 minutes and the correct password receives HTTP 401 with the generic error (`test_five_wrong_login_passwords_lock_account_for_15_minutes`). |
| `<script>alert(1)</script>` as a rider name | Display the name as escaped text; do not render the script. | Pass: escaped markup appears in the rider list and raw markup does not (`test_rider_name_script_is_escaped_in_admin_list`). |
| A Seller requests `/admin/riders` or submits its form | Deny access with HTTP 403. | Pass: page and create requests return HTTP 403 (`test_only_admin_can_view_and_submit_rider_management`). |
| A disabled rider submits the correct password at login | Refuse login with the generic error. | Pass: HTTP 401 with “Invalid email or password.” (`test_disabled_rider_cannot_log_in_and_actions_are_audited`). |
| Replay a copied session cookie after logout | Treat the request as logged out and redirect to login. | Pass: the replayed cookie is denied access and redirected to login (`test_logout_invalidates_a_copied_session_cookie`). |

# Module 2 security test cases (Parcel Registration and Public Tracking)

**Owner:** Syabil · Verified with `python -m pytest tests/test_m2.py -q`: **24 passed**.
All records used in these tests are fake demo data; the tests use a temporary SQLite database.

| ID | Input or attack | Expected result | Actual result | Owner |
|---|---|---|---|---|
| M2-01 | Search own parcels with `' OR '1'='1` while another seller has a private parcel | Search completes without a database error and never returns another seller's parcel | Pass: HTTP 200, generic “No parcels found.” result, and the other seller's recipient is absent (`test_sql_injection_in_seller_parcel_search_stays_scoped_to_owner`) | Syabil |
| M2-02 | Register a parcel with `<script>alert(1)</script>` as the delivery address | Accept valid text but escape it when rendered; do not execute the script | Pass: seller detail contains escaped markup and no raw script tag (`test_script_in_address_is_escaped_on_seller_parcel_detail`) | Syabil |
| M2-03 | Submit phone `abc` or weight `-2` during registration | Reject invalid values with field-specific messages; do not create the parcel | Pass: HTTP 400 with the expected phone or weight error (`test_registration_validation_shows_field_error_and_keeps_input`, parameter cases `recipient_phone/abc` and `weight_kg/-2`) | Syabil |
| M2-04 | Seller changes the parcel detail URL to another seller's parcel ID or an unknown ID | Deny access on the server with HTTP 403 | Pass: both other-seller and unknown IDs return HTTP 403 (`test_other_seller_and_unknown_parcel_ids_both_return_403`) | Syabil |
| M2-05 | Submit a made-up sequential tracking number | Show a generic “No parcel has that tracking number” result; reveal no recipient details | Pass: HTTP 200 with the generic not-found message and no demo recipient, phone, or address (`test_unknown_or_sequential_tracking_number_returns_generic_not_found`) | Syabil |
| M2-06 | Submit 25 tracking lookups from the same client within one minute | Allow the first 20; rate-limit the remaining requests with HTTP 429 and a generic message | Pass: first 20 return HTTP 200; lookups 21–25 return HTTP 429 (`test_25_tracking_lookups_in_one_minute_get_429_after_limit`) | Syabil |
| M2-07 | Publicly track an existing parcel by its tracking number | Show parcel status only; never show recipient name, phone, or address | Pass: HTTP 200 shows “Registered” while all three personal-data values are absent (`test_public_tracking_never_shows_recipient_personal_data`) | Syabil |

# Module 3 security test cases (Delivery Update and Admin Dashboard)

**Owner:** Aizat · Verified with `python -m pytest tests -q`: **150 passed** in the latest full-suite run.
Module 3 and policy P3 have **100 automated tests** in `tests/test_m3.py`, `tests/test_p3.py` and the
`SR3` tests in `tests/test_security.py`. All data used is fake demo data from `app/seed.py`.

**12 input types tested:** malicious file uploads, oversized files, fake or broken images, made-up
status values, skipped or backward status steps, changed IDs in the URL, tampered form fields,
missing CSRF tokens, scripts in stored text (XSS), path tricks (`../`), wrong-role access, and
logged-out access.

| ID | Input or attack | Expected result | Actual result | Owner |
|---|---|---|---|---|
| M3-01 | Upload `shell.php` (a PHP script) as the delivery photo | Rejected with "Please upload a JPG or PNG photo under 5 MB."; status unchanged; nothing saved | Pass: generic message, status stays Out for Delivery, no file in `uploads/`, attempt logged (`test_SR3_4_non_images_rejected[shell.php]`) | Aizat |
| M3-02 | Upload a text file renamed `shell.php.jpg` | Rejected: Pillow finds no real image inside | Pass: same generic message, nothing saved (`test_SR3_4_non_images_rejected[shell.php.jpg]`) | Aizat |
| M3-03 | Upload a real GIF, and a GIF renamed to `.jpg`; a PNG renamed to `.jpg` | Rejected: only real JPEG or PNG whose content matches the extension | Pass: all rejected (`test_SR3_4_gif_rejected`, `test_SR3_4_extension_must_match_content`) | Aizat |
| M3-04 | Upload a file over 5 MB | HTTP 413 before the file is read; status unchanged; logged | Pass: HTTP 413 with "Please upload a JPG or PNG photo under 5 MB.", logged as "Blocked upload over 5 MB" (`test_SR3_4_file_over_5mb_gets_413`) | Aizat |
| M3-05 | Upload a cut-off (broken) JPEG, and a 45-megapixel "image bomb" PNG | Rejected without crashing the server | Pass: both rejected with the generic message (`test_SR3_4_broken_image_rejected`, `test_SR3_4_image_bomb_rejected`) | Aizat |
| M3-06 | A real JPEG with hidden EXIF text and `<?php ... ?>` code glued to the end | Accepted as a photo, but the saved copy contains neither | Pass: saved file has no `<?php` and no hidden text (`test_SR3_4_hidden_data_and_appended_code_removed`) | Aizat |
| M3-07 | Valid JPG, `PROOF.JPEG` and PNG photos | Accepted; saved under a random 32-character name in `uploads/` (outside `app/static`); not reachable by URL | Pass: random names, `/static/...` and `/uploads/...` return 404 (`test_SR3_4_valid_photo_saved_with_random_name`, `test_SR3_4_uploads_are_not_public`) | Aizat |
| M3-08 | Mark Delivered or Failed with no photo, or an empty file field | Rejected; status unchanged | Pass (`test_SR3_4_no_photo_rejected`) | Aizat |
| M3-09 | Status value `Lost`, empty, `assigned`, `Registered`, or `Out for Delivery<script>` | Rejected with "That status change isn't allowed for this parcel."; status and history unchanged; logged | Pass: HTTP 302 back with the message, no new history row (`test_SR3_3_invalid_or_skipped_status_rejected`) | Aizat |
| M3-10 | `Delivered` straight from `Assigned` (skipping a step); any change after Delivered | Rejected; only Assigned → Out for Delivery → Delivered/Failed allowed | Pass (`test_SR3_3_invalid_or_skipped_status_rejected[Delivered]`, `test_SR3_3_finished_delivery_cannot_change`) | Aizat |
| M3-11 | Rider Ali changes the URL to Rider Siti's parcel (`/rider/parcels/4`), views or updates it | HTTP 403; logged | Pass: HTTP 403 for viewing and updating, "Blocked access: rider 3 tried parcel 4" in the log (`test_SR3_2_rider_cannot_update_another_riders_parcel`, `test_P5_blocked_access_is_logged`) | Aizat |
| M3-12 | A non-existent parcel ID (`/rider/parcels/99999`) | HTTP 403, same as "not yours", so IDs can't be guessed | Pass (`test_SR3_2_unknown_parcel_id_is_403`) | Aizat |
| M3-13 | Seller or Rider opens or submits `/admin/assign`; Seller or Admin tries a rider status update | HTTP 403; nothing changes | Pass (`test_SR3_1_only_admin_opens_or_submits_assign`, `test_SR3_1_only_riders_can_update_status`) | Aizat |
| M3-14 | Logged-out visitor opens `/admin/assign`, `/admin/parcels`, a rider status update or `/photos/<id>` | Redirected to the login page | Pass (`test_SR3_1_assign_page_needs_login`, `test_SR3_1_admin_parcel_pages_need_login`, `test_logged_out_user_is_sent_to_login`, `test_P1_logged_out_visitor_sent_to_login`) | Aizat |
| M3-15 | Tampered assign form: rider ID `abc`, empty, `1 OR 1=1`, `-1`, `99999`, a seller's or admin's ID, a disabled rider | Rejected; parcel stays Registered with no rider | Pass (`test_SR3_1_tampered_rider_id_rejected`, `test_SR3_1_cannot_assign_to_a_seller_or_admin`, `test_SR3_1_cannot_assign_to_a_disabled_rider`) | Aizat |
| M3-16 | Tampered assign form: the ID of a parcel already Out for Delivery, to hand it to another rider | Rejected; parcel keeps its rider and status | Pass (`test_SR3_1_cannot_reassign_a_parcel_already_on_its_way`) | Aizat |
| M3-17 | Status update or assign form sent without a CSRF token | HTTP 400 with the site's error page; nothing changes; logged | Pass: "This form has expired. Reload the page and try again.", logged with user and page (`test_SR3_6_status_update_without_csrf_token_rejected`, `test_SR3_6_csrf_page_is_styled_and_logged`) | Aizat |
| M3-18 | `<script>alert('xss')</script>` as recipient name and `<img src=x onerror=alert(1)>` as address | Shown as plain text on rider and Admin pages, never run | Pass: escaped as `&lt;script&gt;` (`test_SR3_6_script_in_recipient_name_is_escaped_on_module3_pages`) | Aizat |
| M3-19 | Another rider or another seller opens `/photos/<id>` | HTTP 403; logged. The assigned rider, Admin and owning seller get the image | Pass (`test_P1_other_rider_and_other_seller_get_403`, `test_P1_allowed_people_can_view_photo`, `test_P5_blocked_photo_access_is_logged`) | Aizat |
| M3-20 | Path tricks: `/photos/../app/__init__.py`, `..%2f` encoded, and a database row whose file name is `../app/__init__.py` or `notes.txt` | No other file is ever sent (403 or 404) | Pass (`test_P3_path_tricks_cannot_reach_other_files`, `test_P3_unsafe_name_in_database_is_never_sent`) | Aizat |
| M3-21 | `/admin/parcels?status=' OR '1'='1` | Unknown status ignored safely (redirect to the full list); ORM query only | Pass (`test_unknown_status_filter_is_ignored_safely`) | Aizat |
| M3-22 | Admin dashboard and parcel list | Counts and tracking numbers only: no recipient names, phones or addresses (P3) | Pass (`test_SR3_7_dashboard_has_no_personal_data`, `test_SR3_7_parcel_list_has_no_personal_data`) | Aizat |
| M3-23 | Valid status changes | Each change saved in `status_history` with rider ID and time (P5) | Pass (`test_SR3_3_valid_route_is_logged_with_rider_and_time`, `test_admin_parcel_page_shows_history_with_who_and_photo`) | Aizat |

## Policy P3 test cases (personal data retention, group task led by Aizat)

| ID | Input | Expected result | Actual result | Owner |
|---|---|---|---|---|
| P3-01 | Run `flask --app app anonymise-old-parcels` with one parcel delivered 400 days ago and one 30 days ago | Old parcel's name, phone and address become `[removed]` and its photo file is deleted; the newer one is untouched | Pass (`test_P3_old_delivered_parcel_is_anonymised_and_new_one_untouched`) | Aizat |
| P3-02 | Same, for Failed parcels | Failed parcels are cleaned 12 months after they were marked Failed | Pass (`test_P3_old_failed_parcel_is_anonymised_too`) | Aizat |
| P3-03 | Parcels finished 364 and 366 days ago | 364 days kept; 366 days cleaned | Pass (`test_P3_twelve_month_boundary`) | Aizat |
| P3-04 | Very old parcels that are still Registered, Assigned or Out for Delivery | Never touched | Pass (`test_P3_unfinished_parcels_are_never_touched`) | Aizat |
| P3-05 | `--dry-run`; a badly formatted `--as-of` date; a database row with a non-photo file name | Dry run changes nothing; bad date refused; only real photo files are deleted | Pass (`test_P3_dry_run_changes_nothing`, `test_P3_bad_date_is_rejected`, `test_P3_only_real_photo_files_are_deleted`) | Aizat |
| P3-06 | Check the log after a clean-up | Only counts are logged, no names, phones, addresses or tracking numbers | Pass (`test_P3_log_has_counts_but_no_personal_data`) | Aizat |

### Still to add (after the site is online, Task 15 and Task 20)

- **Burp Suite:** capture a rider's status update and change `new_status` to `Lost`, and change the parcel
  ID to another rider's parcel; capture a photo upload and rename the file to `shell.php`. Expected
  results are M3-09, M3-11 and M3-01. Screenshots go in `docs/screenshots/`.
- **OWASP ZAP:** a scan of the live site, with any Module 3 findings and how they were handled.
