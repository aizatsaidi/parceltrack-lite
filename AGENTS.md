# Instructions for AI coding assistants

You are helping one member of a three-person university group build **ParcelTrack Lite**,
a secure parcel tracking web app (course STTCK3033 Secure Software Development, UUM).
Read this whole file before making any change.

## Who you are working for

Each member owns ONE module and is **marked individually** on it, including a live
demonstration where they must **explain their own code and answer questions**.
Using AI is allowed by the lecturer, but the member must understand every line.

At the start of a session, ask which member you are helping if it is not clear, then read
their task brief:

| Member | Module | Task brief | Their folder |
|---|---|---|---|
| Aqil | M1 Login and User Management | `docs/tasks/M1-aqil.md` | `app/auth/`, `app/templates/auth/` |
| Syabil | M2 Parcel Registration and Public Tracking | `docs/tasks/M2-syabil.md` | `app/parcels/`, `app/templates/parcels/` |
| Aizat | M3 Delivery Update and Admin Dashboard | `docs/tasks/M3-aizat.md` | `app/delivery/`, `app/templates/delivery/` |

## Rules

1. **Stay inside the member's own module folder.** Do not edit another member's module.
2. **Shared files** (`app/__init__.py`, `app/models.py`, `app/security.py`, `app/seed.py`,
   `app/templates/base.html`, `requirements.txt`) may be changed only when the task really
   needs it. Keep the change small, never remove or rename existing columns or functions,
   and tell the member to inform the group.
3. **Security controls are checked on the server** for every request. Hiding a button or
   menu item is never access control.
4. **Database:** use SQLAlchemy ORM queries only (parameterised). Never build SQL with
   string formatting.
5. **Output:** rely on Jinja auto-escaping. Never use `|safe` or `Markup` on user data.
6. **Forms:** every POST form includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
7. **Errors (policy P4):** users see short generic messages; technical details go to
   `app.logger` only. Never set `debug=True`.
8. **Secrets and data (P4):** no passwords, keys or real personal data in code or tests.
   Use fake data like the accounts in `app/seed.py`.
9. **Logging (P5):** status changes and logins are logged without passwords or full addresses.
10. **Tests:** add tests for the new security controls in `tests/test_<module>.py`
    (for example `tests/test_m3.py`), following the style of `tests/test_security.py`.
    Before you finish, run `python -m pytest tests -q`; all tests must pass.
11. **Do not commit or push.** The member reviews the change and commits it themselves
    from their own GitHub account, with a message starting with the module code,
    for example `M3: add rider status update`.

## How to work with the member

- Work on **one checklist item at a time** from their task brief, not the whole module at once.
- Before writing code, explain in plain, beginner-friendly language what you will build and why.
- After each change, explain **what each new part does and which security requirement it meets**,
  so the member can explain it in the live demo.
- End each item with: the files changed, how to test it by hand in the browser, and
  two or three questions the lecturer might ask about it, with short answers.

## Running the project

```
pip install -r requirements.txt
python run.py                 # http://127.0.0.1:5000 (fake demo logins are in README.md)
python -m pytest tests -q     # security tests
```

Delete `parceltrack.db` to reset the demo data after changing `app/models.py` or `app/seed.py`.

## Marking (per member, 40 raw marks = 30%)

1a module functions (5) · 1b deployment and integration on a cloud server (10; local only −5) ·
2a security controls (6) · 2b policies and error handling (4) ·
3 security testing, more than 5 input types documented (10) · 4 live demo and Q&A (5).
