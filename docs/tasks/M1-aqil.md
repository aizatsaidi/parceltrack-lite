# M1 · Login and User Management · Aqil

Policies: **P1, P2, P5** · Folder: `app/auth/`, `app/templates/auth/` · Tests: `tests/test_m1.py`

## Already working

- Login and logout for Seller, Rider and Admin (`/login`, `/logout`)
- Seller self-registration with a 10-character minimum (`/register`)
- Lockout for 15 minutes after 5 failed logins; one generic error message
- Session cleared at login and logout; logins and failed logins saved in `login_events`

## To do (one item at a time)

1. **Switch password hashing to bcrypt or Argon2.** The rubric names these two; the current
   code uses Werkzeug's default (scrypt). Use the `bcrypt` or `argon2-cffi` package, add it to
   `requirements.txt`, and use it in `register()`, `login()` and `app/seed.py`.
   Old hashes do not need migrating: delete `parceltrack.db` and reseed.
2. **Admin creates Rider accounts.** An Admin-only page (`/admin/riders`) listing riders,
   with a form for name, email and a temporary password (at least 10 characters).
   Use `role_required("admin")` from `app/security.py`.
3. **Admin disables and re-enables Rider accounts** (P1: disabled the day a rider leaves).
   Set `is_active_account = False`. A disabled rider must be logged out on their next
   request (the `user_loader` in `app/__init__.py` already does this) and must not be able
   to log in again.
4. **Change password page** for any logged-in user: current password, new password
   (at least 10 characters), confirm. Check the current password first, then hash the
   new one and start a fresh session.
5. **Tests** in `tests/test_m1.py`, at least 6 input types.

## Rubric key controls (criterion 2a)

Parameterised queries · password hashing (bcrypt or Argon2) · lockout or rate limit on login ·
session regenerated on login and destroyed on logout · role checked on the server ·
logins logged without passwords.

## Rubric suggested tests (criterion 3)

| Input | Expected result |
|---|---|
| `' OR '1'='1' -- ` as the email | Login fails with the generic message |
| Password shorter than 10 characters at registration or change password | Rejected with a clear message |
| Wrong password 5 times, then the right one | Account locked; login refused for 15 minutes |
| `<script>alert(1)</script>` in the name field | Shown as plain text; no pop-up |
| Opening `/admin/riders` as a Seller | 403 |
| Disabled rider tries to log in | Generic login error |

## Things to be ready to explain in the demo

Why bcrypt/Argon2 instead of storing the password; why the error message never says which
part was wrong; how the lockout works; why the session is cleared at login; where the role
check happens on the server.
