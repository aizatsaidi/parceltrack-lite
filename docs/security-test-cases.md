# Module 1 security test cases

Verified with `python -m pytest tests -q`: **48 passed**.

| Input | Expected result | Actual result |
|---|---|---|
| `' OR '1'='1' -- ` in the login email field | Login fails with the generic error; no user is authenticated. | Pass: HTTP 401 with “Invalid email or password.” (`test_sql_injection_email_gets_generic_login_error`) |
| A password shorter than 10 characters at registration or password change | Reject the form and explain the minimum length. | Pass: both forms return HTTP 400 with the minimum-length message (`test_short_registration_password_is_rejected`, `test_change_password_validates_current_short_and_confirm_passwords`). |
| Five incorrect login passwords followed by the correct password | Lock the account for 15 minutes; the correct password is refused during the lockout. | Pass: the stored lockout is about 15 minutes and the correct password receives HTTP 401 with the generic error (`test_five_wrong_login_passwords_lock_account_for_15_minutes`). |
| `<script>alert(1)</script>` as a rider name | Display the name as escaped text; do not render the script. | Pass: escaped markup appears in the rider list and raw markup does not (`test_rider_name_script_is_escaped_in_admin_list`). |
| A Seller requests `/admin/riders` or submits its form | Deny access with HTTP 403. | Pass: page and create requests return HTTP 403 (`test_only_admin_can_view_and_submit_rider_management`). |
| A disabled rider submits the correct password at login | Refuse login with the generic error. | Pass: HTTP 401 with “Invalid email or password.” (`test_disabled_rider_cannot_log_in_and_actions_are_audited`). |
| Replay a copied session cookie after logout | Treat the request as logged out and redirect to login. | Pass: the replayed cookie is denied access and redirected to login (`test_logout_invalidates_a_copied_session_cookie`). |
