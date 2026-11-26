# ParcelTrack Lite

STTCK3033 Secure Software Development: group project for RapidExpress Sdn. Bhd.
Stack: Python Flask + MySQL (SQLite for local demos).

| Module | Owner | Folder |
|---|---|---|
| 1 · Login and User Management | Aqil | `app/auth/` |
| 2 · Parcel Registration and Public Tracking | Syabil | `app/parcels/` |
| 3 · Delivery Update and Admin Dashboard | Aizat | `app/delivery/` |

Shared by the group: `app/__init__.py`, `app/models.py`, `app/security.py`, `app/templates/base.html`.

---

## How to run it on your laptop (first time)

You need **Python 3.10 or newer** installed. Check by typing `python --version` in a terminal.
If it isn't installed, get it from python.org. On Windows, tick **"Add Python to PATH"** during install.

1. Unzip the project folder. Open a terminal **inside** the `parceltrack-lite` folder.
   (Windows: open the folder, click the address bar, type `cmd`, press Enter.)
2. Install the packages (only once):
   ```
   pip install -r requirements.txt
   ```
3. Start the website:
   ```
   python run.py
   ```
4. Open **http://127.0.0.1:5000** in your browser.

To stop it, press `Ctrl + C` in the terminal. To start again, repeat step 3 only.

To reset all demo data, stop the website, delete the file `parceltrack.db`, and start it again.

## Demo logins (fake test accounts only)

| Role | Email | Password |
|---|---|---|
| Admin | admin@rapidexpress.test | AdminDemo#2026 |
| Seller | seller@shop.test | SellerDemo#2026 |
| Rider | ali@rapidexpress.test | RiderAliDemo#2026 |
| Rider | siti@rapidexpress.test | RiderSitiDemo#2026 |

Demo tracking numbers: `RX-DEMO7KQ2M9`, `RX-DEMOP4T8WZ`, `RX-DEMO9HN3QX`, `RX-DEMOB6R2VK`

---

## Progress demo script (about 1–2 minutes each)

**Aqil (Module 1): Login**
1. Go to *Log in*. Type the admin email with a wrong password. You see only "Invalid email or password". It doesn't say which part was wrong.
2. Log in properly as seller, then log out. Log in as a rider and show they land on a different page.
3. Say: passwords are stored as hashes, and 5 wrong tries lock the account for 15 minutes.

**Syabil (Module 2): Register parcel and tracking**
1. Log in as the seller. Click *+ Register parcel*, fill in fake details, and submit. A random tracking number appears.
2. Log out. Open *Track parcel* and enter that number. Only the status and time show, with no name, phone or address.
3. Say: the tracking number comes from a secure random generator, so it can't be guessed.

**Aizat (Module 3): Assign parcels**
1. Log in as admin. Show the summary counts, pick a rider for a parcel, and click *Assign*. The counts change.
2. Log out and log in as Rider Ali. *My deliveries* shows only Ali's parcels. Click one: the address in the browser ends in a number, e.g. `/rider/parcels/3`.
3. Change that number to `4` (Siti's parcel) and press Enter. You get **403 Forbidden**.
4. Say: access is checked on the server for every request, not just hidden in the menu.

## Running the security tests

```
pip install pytest
python -m pytest tests -v
```
Each test checks one security requirement from the slides (SR1.x, SR2.x, SR3.x).

## Working on your module

Each member has a task brief in `docs/tasks/` with their to-do items, the rubric's security controls
and suggested tests. You are marked on explaining **your own code** in the live demo.

1. **Get the code (first time):** `git clone https://github.com/aizatsaidi/parceltrack-lite.git`
   (or GitHub Desktop → Clone). Before each work session: `git pull`.
2. **Open your task brief:** `docs/tasks/M1-aqil.md`, `docs/tasks/M2-syabil.md` or `docs/tasks/M3-aizat.md`.
3. **Do one item at a time.** Make sure you understand every line, test it in the browser, and run
   `python -m pytest tests -q`.
4. **Commit from your own account** with a message starting with your module code:
   `git add -A` → `git commit -m "M3: add rider status update"` → `git pull` → `git push`.
   Then tick the item in the checklist below.
5. **Only edit your own module folder.** Tell the group before changing shared files
   (`models.py`, `__init__.py`, `security.py`, `seed.py`, `base.html`, `requirements.txt`).

## UI guide (use these for every new page)

All styles live in `app/static/css/app.css`. Don't add `<style>` blocks, new colours or external
fonts or CSS. Fonts (Archivo and IBM Plex Mono) are bundled, so the site works offline.

**Page setup**

```html
{% extends "base.html" %}
{% from "_macros.html" import status_badge, waybill, route %}
{% block title %}Page name{% endblock %}
{% block page_class %}page-narrow{% endblock %}   {# optional: narrow pages for forms and phones #}
{% block content %} … {% endblock %}
```

**Macros** (`app/templates/_macros.html`)

| Macro | Use it for |
|---|---|
| `{{ status_badge(parcel.status) }}` | Every status shown anywhere. Coloured pill that always includes the word |
| `{{ waybill(parcel.tracking_no) }}` | Every tracking number. `small=true` inside tables and lists |
| `{{ route(events) }}` | Status timeline. `events` = list of `(status, datetime)`, oldest first |

**Classes**

| Class | What it is |
|---|---|
| `page-head` | Row with the page title on the left and an action on the right |
| `panel`, `panel-title` | White box for a group of content |
| `facts` | Label and value list (`<dl class="facts"><dt>…</dt><dd>…</dd></dl>`) |
| `field`, `input`, `select`, `textarea`, `hint` | Form parts. Wrap each label and input in `<div class="field">` |
| `inline-form` | Field and button on one line (search, assign) |
| `button` | Main action (dark). `button-tape` = the one most important action on a page (yellow). `button-ghost` = secondary. `button-small`, `button-block` |
| `table-wrap` + `data-table` | Tables. `td class="empty"` for the "nothing here" row |
| `job-list` + `job` | Big tappable rows for riders on phones |
| `tally` + `bin bin-<status>` | Status count boxes on the dashboard |
| `notice notice-success / -danger / -warning / -info` | Messages. Flash messages already use these |
| `empty-state` | Box shown when a list is empty, telling the user what to do |
| `back-link`, `muted`, `small`, `mono` | Small helpers |

Flash categories: `success`, `danger`, `warning`, `info`. Every POST form still needs the CSRF hidden field.

## Checklist to Week 14 (matches the lecturer's rubric)

Tick items off as they are done. Each member writes the code for their own module (rubric rule 5).
Rubric marks per member: 1a functions (5), 1b deployment and integration (10), 2a security controls (6),
2b policies and error handling (4), 3 security testing (10), 4 live demo and Q&A (5) = 40 raw marks → 30%.

### Module 1: Login and User Management (Aqil) · policies P1, P2, P5

- [x] Login and logout for Seller, Rider and Admin
- [x] Seller self-registration (password at least 10 characters)
- [x] Lockout after 5 failed logins; generic "Invalid email or password"; logins logged without passwords
- [ ] **Switch password hashing to bcrypt or Argon2** (rubric names these two; current code uses Werkzeug scrypt)
- [ ] Admin creates Rider accounts
- [ ] Admin disables Rider accounts (P1: disabled the day a rider leaves)
- [ ] Change password page
- [ ] Tests from the rubric: SQL injection in username, weak or short password, repeated wrong passwords, script in name field, opening an admin page as Seller

### Module 2: Parcel Registration and Public Tracking (Syabil) · policies P1, P3, P4

- [x] Seller registers a parcel with server-side validation (phone, address, weight)
- [x] Cryptographically random, unique tracking number
- [x] Seller views and searches own parcels only
- [x] Public tracking shows status, date and time only (no name, phone or address)
- [ ] **Rate limit on tracking lookups** (stops guessing tracking numbers)
- [ ] Tests from the rubric: SQL injection in search, XSS in address, invalid phone or negative weight, changing a parcel ID in the URL, guessed or sequential tracking number, many rapid lookups

### Module 3: Delivery Update and Admin Dashboard (Aizat) · policies P1, P3, P5

- [x] Admin assigns parcels to active riders (status → Assigned, logged with user and time)
- [x] Rider views assigned parcels only; any other parcel ID returns 403
- [x] Admin dashboard of parcel counts by status (Admin only, no personal data)
- [ ] **Rider status update** in order only: Assigned → Out for Delivery → Delivered or Failed; reject any other status value
- [ ] **Proof-of-delivery photo upload**: one JPG or PNG; check type, size and real image content; rename to a random name; store outside the web folder
- [ ] Every status change logged in `status_history` with user and time, without addresses (P5)
- [ ] Tests from the rubric: uploading `.php` or `shell.php.jpg`, oversized image, invalid status value, updating a parcel not assigned to the rider, opening the dashboard without Admin login

### Whole group

- [ ] Integrate all modules with the real login and move the database to MySQL
- [ ] Deploy on a cloud server with HTTPS (local only loses 5 marks in criterion 1b) and run the Week 14 demo from it
- [ ] Delete or anonymise recipient data 12 months after delivery (P3)
- [ ] Security scans with OWASP ZAP and request tampering with Burp Suite
- [ ] **Security test case document**, organised by module: input, expected result, actual result, owner's name. More than 5 input types per module for full marks in criterion 3
- [ ] Rehearse the live demo: about 10 minutes each, showing failed attack attempts and explaining your own code
