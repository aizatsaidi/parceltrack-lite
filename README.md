# ParcelTrack Lite

STTCK3033 Secure Software Development: group project for RapidExpress Sdn. Bhd.
Stack: Python Flask + MySQL (SQLite for local demos).

| Module | Owner | Folder |
|---|---|---|
| 1 · Login and User Management | Member 1 [Name] | `app/auth/` |
| 2 · Parcel Registration and Public Tracking | Member 2 [Name] | `app/parcels/` |
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

**Member 1: Login**
1. Go to *Log in*. Type the admin email with a wrong password. You see only "Invalid email or password". It doesn't say which part was wrong.
2. Log in properly as seller, then log out. Log in as a rider and show they land on a different page.
3. Say: passwords are stored as hashes, and 5 wrong tries lock the account for 15 minutes.

**Member 2: Register parcel and tracking**
1. Log in as the seller. Click *+ Register parcel*, fill in fake details, and submit. A random tracking number appears.
2. Log out. Open *Track parcel* and enter that number. Only the status and time show, with no name, phone or address.
3. Say: the tracking number comes from a secure random generator, so it can't be guessed.

**Member 3 (Aizat): Assign parcels**
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

## Not finished yet (next steps)

- Module 1: Admin creates and disables Rider accounts; change password page
- Module 2: Rate limit on the tracking page
- Module 3: Rider status update in the correct order; secure proof-of-delivery photo upload
- Group: Move to MySQL and deploy on a cloud server with HTTPS
