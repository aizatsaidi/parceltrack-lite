# ParcelTrack Lite

[![Security tests](https://github.com/aizatsaidi/parceltrack-lite/actions/workflows/tests.yml/badge.svg)](https://github.com/aizatsaidi/parceltrack-lite/actions/workflows/tests.yml)

STTCK3033 Secure Software Development: group project for RapidExpress Sdn. Bhd.
Stack: Python Flask + MySQL (SQLite for local demos).

| Module | Owner | Folder |
|---|---|---|
| 1 · Login and User Management | Aqil | `app/auth/` |
| 2 · Parcel Registration and Public Tracking | Syabil | `app/parcels/` |
| 3 · Delivery Update and Admin Dashboard | Aizat | `app/delivery/` |

Shared by the group: `app/__init__.py`, `app/models.py`, `app/security.py`, `app/seed.py`,
`app/templates/base.html`, `app/templates/_macros.html`, `app/static/`.

---

## Get the project (first time)

1. Install **Python 3.10 or newer** from python.org. On Windows, tick **"Add Python to PATH"** during install.
   Check it works by typing `python --version` in a terminal.
2. Install **GitHub Desktop**, sign in, then **File → Clone repository → aizatsaidi/parceltrack-lite**.
   Save it outside OneDrive, for example `C:\parceltrack-lite`.
3. Open that folder, click the address bar, type `cmd` and press Enter. Then install the packages (only once):
   ```
   pip install -r requirements.txt
   ```

## Run it

```
python run.py
```

Open **http://127.0.0.1:5000** in your browser. To stop it, press `Ctrl + C` in the terminal.

- **Live reload:** while it runs, saving any file in `app/` refreshes the browser by itself (about 1 second).
  Python changes restart the website first. This only happens with `python run.py` on your own laptop,
  never on the cloud server, and Flask's debug mode stays off (P4).
- **To reset the demo data,** stop the website, delete `parceltrack.db`, and start it again.

## Optional: run with MySQL

By default, the app uses the local SQLite file `parceltrack.db`; no database server is needed. The
tests explicitly use temporary SQLite databases. To use MySQL instead, install the packages from
`requirements.txt` and create the database and a dedicated application account. Run these statements
in MySQL as a database administrator, replacing the example password with a unique secret:

```sql
CREATE DATABASE parceltrack CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'parceltrack_app'@'127.0.0.1' IDENTIFIED BY 'replace-with-a-long-random-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON parceltrack.* TO 'parceltrack_app'@'127.0.0.1';
```

The app account only receives the data access needed at runtime. Create the tables with an admin
account by running `mysql -u root -p parceltrack < schema.sql`. Then copy `.env.example` to `.env`,
set a random `SECRET_KEY`, and set `DATABASE_URL` to the app account's URL, for example:

```text
DATABASE_URL=mysql+pymysql://parceltrack_app:YOUR_DB_PASSWORD@127.0.0.1:3306/parceltrack
```

Encode reserved characters in the URL username or password (for example, `@` as `%40`). Start the
app with `python run.py`; it seeds the fake demo data on the first run, using the configured database.
Keep `.env` private; it is excluded from Git. For a remote MySQL server, create the app user for the
specific application host instead of granting access from every host, and use the server's TLS setup.

## Demo logins (fake test accounts only)

| Role | Email | Password | Lands on |
|---|---|---|---|
| Admin | admin@rapidexpress.test | AdminDemo#2026 | Dashboard |
| Seller | seller@shop.test | SellerDemo#2026 | My parcels |
| Rider | ali@rapidexpress.test | RiderAliDemo#2026 | My deliveries |
| Rider | siti@rapidexpress.test | RiderSitiDemo#2026 | My deliveries |

| Tracking number | Status | Rider |
|---|---|---|
| `RX-DEMO7KQ2M9`, `RX-DEMOP4T8WZ` | Registered | none yet |
| `RX-DEMO9HN3QX` | Assigned | Ali |
| `RX-DEMOB6R2VK` | Assigned | Siti |
| `RX-DEMOT5W8LC` | Out for Delivery | Ali |
| `RX-DEMOH2Y6RF` | Delivered | Siti |

---

## Tasks: who does what

The full task list is on GitHub: **[Issues](https://github.com/aizatsaidi/parceltrack-lite/issues)**
(click **Sort → Oldest** so Task 1 is on top). Each task says what to build, which files to change,
the security rules, and **"Finish these first"** if it has to wait for another task.
A task closes by itself when its work is merged with `Closes #<number>` in the pull request or commit.

| Who | Tasks | Group tasks they lead |
|---|---|---|
| **Aizat** | 6, 9, 12, 14, 19 | 1 (design, done), 2 (automatic tests), 16 (delete old data, P3) |
| **Aqil** | 4, 7, 10, 13, 17 | 20 (security test case document) |
| **Syabil** | 5, 8, 11, 18 | 3 (MySQL), 15 (deploy online with HTTPS) |

Do your tasks in number order. Tasks next to each other belong to different people, so you can all work
at the same time.

## How to work on a task

1. **Get the latest code:** in GitHub Desktop, make sure **Current branch** is `main`, then click
   **Fetch origin** and **Pull origin**.
2. **Do the task** (yourself or with an AI tool opened on your `parceltrack-lite` folder). Change only your
   own module folder. Tell the group before changing shared files.
3. **Check it:** run the website and test it in the browser, then run the security tests (below).
   Make sure you understand every line; the lecturer asks you to explain your own code.
4. **Commit from your own account:** your changed files appear on the left (**Changes**) in GitHub Desktop.
   Write a **Summary** starting with the task, for example `Task 6: rider status update`, and add
   `Closes #6` in the **Description**. Click **Commit to main**, then **Push origin**.
5. Tell the group so they can **Pull origin**.

## Security tests

```
pip install pytest
python -m pytest tests -v
```

Each test checks one security requirement from the slides (SR1.x, SR2.x, SR3.x). All tests must pass
before you push. GitHub also runs them automatically on every push (the **Security tests** badge at the top
and the ✓ or ✗ next to each commit); a red ✗ means someone's change broke a test, so fix it first. New tests for each module go in `tests/test_m1.py`, `tests/test_m2.py` and `tests/test_m3.py`.

---

## Week 14 live demo

30 minutes for the group, about **10 minutes per member**, on the **live cloud website** (rubric 1b:
a local-only demo loses 5 marks). For your own module:

1. **Show it working:** the normal flow from start to finish.
2. **Show attacks failing** (rubric 4 asks for failed attack attempts), for example:
   - **Aqil:** SQL injection in the email box, a short password, 5 wrong passwords then lockout, a Seller opening an admin page
   - **Syabil:** SQL injection in search, a script in the address, another seller's parcel ID in the URL, a guessed tracking number, too many lookups
   - **Aizat:** uploading `shell.php` or `shell.php.jpg`, an oversized image, a made-up status value, a rider opening another rider's parcel (try `/rider/parcels/4` as Ali: **403**)
3. **Show the evidence:** the log or status history entry the action created.
4. **Explain your own code** and answer questions: where the check happens, and which threat or policy it stops.

---

## UI guide (use these for every new page)

All styles live in `app/static/css/app.css`, with light and dark mode built in (light by default). Don't add
`<style>` blocks, new colours, or external fonts or CSS: the fonts (Inter and IBM Plex Mono) and icons are
bundled, so the site works offline. Logged-in users get the teal gradient sidebar layout automatically; visitors
get the top-bar layout. Theme colours are teal, green and gold; don't use blue or purple.

**Page setup**

```html
{% extends "base.html" %}
{% from "_macros.html" import icon, status_badge, waybill, route, avatar %}
{% block title %}Page name{% endblock %}
{% block content_class %}content-narrow{% endblock %}   {# optional: narrow page (forms, rider pages) #}
{% block topbar_actions %}<a class="button" href="...">{{ icon("plus") }} Action</a>{% endblock %}  {# optional #}
{% block content %}
  <div class="page-head"><div><h1>Title</h1><p>One line explaining the page.</p></div></div>
  …
{% endblock %}
```

**Macros** (`app/templates/_macros.html`)

| Macro | Use it for |
|---|---|
| `{{ icon("truck") }}` | Icons: package, truck, dashboard, search, plus, user, user-plus, phone, pin, weight, clock, check, check-circle, x, alert, info, shield, lock, store, inbox, list, arrow-left, chevron-right, logout, menu, sun, moon |
| `{{ status_badge(parcel.status) }}` | Every status shown anywhere: coloured pill that always includes the word |
| `{{ waybill(parcel.tracking_no) }}` | Every tracking number. `large=true, sub="…"` for page headers |
| `{{ route(events) }}` | Status timeline with progress bar. `events` = list of `(status, datetime)`, oldest first |
| `{{ avatar(name) }}` | Round initials for a person |

**Status colours** (used by badges, tiles, charts and the timeline): Registered = gold,
Assigned = teal, Out for Delivery = orange, Delivered = green, Failed = rose.

**Layout and content**

| Class | What it is |
|---|---|
| `card`, `card-pad`, `card-head`, `card-body`, `card-title` | Content boxes. `card-head` holds a title or search plus a `count` pill. An `icon()` first in `card-title` gets a coloured chip |
| `page-head` | Page title with a one-line description |
| `banner` (+ `banner-warm`) | Gradient welcome or summary strip (teal-green, or warm orange with `banner-warm`). Inside: `actions` (buttons), `banner-icon`, `big` (large number), `meter > span` (progress) |
| `dash-grid` | Three-column row of cards (two on tablets, one on phones) |
| `facts` + `fact` (`k` label, `v` value) | Label and value list with an icon per row |
| `table-wrap` + `data-table` | Tables inside a `card`. `td class="empty"` with a `chip-icon` for the "nothing here" row. `person` = avatar and name |
| `notice notice-success / -danger / -warning / -info` | Messages (put an `icon()` first). Flash messages already use these |

**Colour tiles and data**

| Class | What it is |
|---|---|
| `stats` + `card stat stat-<status>` | Gradient status count cards on the dashboard, with `share > span` bar and `foot` text |
| `summary` + `card tile tile-<colour>` | Gradient summary tiles: `tile-teal`, `tile-gold`, `tile-orange`, `tile-green`, `tile-rose`, `tile-lime` |
| `donut` + `legend` | Status donut chart (see `delivery/assign.html` for how it is built from real counts) |
| `workload`, `activity` | Rider workload bars and the recent activity feed on the dashboard |
| `job-list` + `card job job-<status>` | Big tappable rider rows with a coloured left edge by status |
| `chip-icon` (+ `chip-registered / -assigned / -out / -delivered / -failed`) | Rounded icon square in a status colour |

**Forms and buttons**

| Class | What it is |
|---|---|
| `field`, `input`, `select`, `textarea`, `hint`, `field-icon` | Form parts. Wrap each label and input in `<div class="field">`; `field-icon` puts an icon inside an input |
| `inline-form` | Field and button on one line (search, assign) |
| `button` | Main action (teal-green gradient). `button-secondary`, `button-ghost`, `button-small`, `button-lg`, `button-block`, `button-icon` |
| `back-link`, `muted`, `small`, `mono` | Small helpers |

Flash categories: `success`, `danger`, `warning`, `info`. Every POST form still needs the CSRF hidden field.
