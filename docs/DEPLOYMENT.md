# Deploying ParcelTrack Lite

## 1. Server setup (Task 15, Syabil)

This guide deploys the Flask app on an Ubuntu 24.04 cloud VM behind Gunicorn and Nginx, with a
MySQL database on the same VM and a Let's Encrypt certificate. It uses the service account
`parceltrack` and `/home/parceltrack/parceltrack-lite`; adjust those paths consistently if needed.
Run commands on the server unless a step says otherwise. Replace `tracking.example.com` with a
DNS name you control.

### Before provisioning

1. Create an Ubuntu 24.04 VM with a public IPv4 address. Point the DNS **A** record for your chosen
   hostname to that address and wait until it resolves.
2. In the cloud firewall and the server firewall, allow inbound TCP **22**, **80**, and **443**.
   Do not expose MySQL port **3306**. Restrict SSH (22) to your own IP when the provider supports it.
3. Keep the provider account, SSH private key, domain, `.env`, and database password private.

### Install the app and system packages

Connect with SSH as the VM's initial administrator, then:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip mysql-server nginx ufw certbot python3-certbot-nginx
sudo adduser --system --group --home /home/parceltrack parceltrack
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Clone the repository and install its Python dependencies. Gunicorn is installed in this server's
virtual environment because the local Windows development setup does not need it:

```bash
sudo -u parceltrack git clone https://github.com/aizatsaidi/parceltrack-lite.git /home/parceltrack/parceltrack-lite
cd /home/parceltrack/parceltrack-lite
sudo -u parceltrack python3 -m venv venv
sudo -u parceltrack venv/bin/pip install --upgrade pip
sudo -u parceltrack venv/bin/pip install -r requirements.txt gunicorn
```

### Create the MySQL database

Confirm MySQL listens only on loopback. In `/etc/mysql/mysql.conf.d/mysqld.cnf`, set
`bind-address = 127.0.0.1`, then restart MySQL:

```bash
sudo systemctl enable --now mysql
sudo systemctl restart mysql
sudo ss -lntp | grep 3306
```

The `ss` output should show `127.0.0.1:3306`, not `0.0.0.0:3306` or a public address. Create a
database and restricted runtime account; generate a unique database password and substitute it
below. Use a URL-safe random password (hex is convenient):

```bash
openssl rand -hex 32
sudo mysql
```

At the MySQL prompt, replace `PASTE_RANDOM_HEX_PASSWORD` with the generated value:

```sql
CREATE DATABASE parceltrack CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'parceltrack_app'@'127.0.0.1' IDENTIFIED BY 'PASTE_RANDOM_HEX_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE ON parceltrack.* TO 'parceltrack_app'@'127.0.0.1';
EXIT;
```

Import the checked-in schema using the local MySQL administrator account:

```bash
sudo mysql < /home/parceltrack/parceltrack-lite/schema.sql
```

The app account intentionally has no schema-alteration privileges. Apply future schema changes
with an administrator after backing up the database; do not grant the runtime app account DDL
privileges to make deployment easier.

### Configure secrets and application settings

Create a secret key and the protected environment file. The password generated above is hex, so it
does not need URL encoding:

```bash
cd /home/parceltrack/parceltrack-lite
sudo -u parceltrack cp .env.example .env
sudo -u parceltrack chmod 600 .env
sudo -u parceltrack nano .env
```

Set these values in `.env` (keep it out of Git):

```dotenv
SECRET_KEY=<output of: openssl rand -hex 32>
DATABASE_URL=mysql+pymysql://parceltrack_app:<database-password>@127.0.0.1:3306/parceltrack
SESSION_COOKIE_SECURE=1
```

Use separate strong random values for `SECRET_KEY` and the database password. Confirm the file is
owned by `parceltrack` and mode `600` (`ls -l .env`). The server must run from the project directory
so `python-dotenv` can load this file. `run.py` seeds the fake demo accounts when the app starts.
They use public README credentials, so reset those credentials before allowing public requests to
reach the app. The steps below do that while Nginx serves only an ACME challenge and a 404 page.
Use only fake parcel data in the public demo.

### Install Gunicorn and Nginx configuration

The supplied WSGI wrapper trusts forwarding headers from one local Nginx proxy. Nginx replaces
these headers, and Gunicorn is bound to loopback, so clients cannot connect directly to it. The
single worker is intentional: the current rate limiter stores counters in process memory. Multiple
workers would each have separate counters; use shared Redis-backed rate-limit storage before
increasing the worker count.

```bash
sudo cp /home/parceltrack/parceltrack-lite/deploy/parceltrack.service /etc/systemd/system/parceltrack.service
sudo cp /home/parceltrack/parceltrack-lite/deploy/nginx-bootstrap.conf /etc/nginx/sites-available/parceltrack
sudo nano /etc/nginx/sites-available/parceltrack
sudo install -d -o root -g root -m 755 /var/www/letsencrypt/.well-known/acme-challenge
sudo ln -s /etc/nginx/sites-available/parceltrack /etc/nginx/sites-enabled/parceltrack
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now parceltrack
sudo systemctl enable --now nginx
```

Replace `tracking.example.com` in the bootstrap Nginx file with your real hostname. This temporary
site serves only ACME challenges; all other HTTP requests receive 404 and cannot reach Gunicorn.
The app is running on loopback only.

### Issue the HTTPS certificate before enabling public app access

Make sure the DNS A record points to the VM and inbound port 80 is allowed. Use Certbot's webroot
challenge to request a certificate without proxying requests to the app. Replace the example
hostname and email address:

```bash
sudo certbot certonly --webroot -w /var/www/letsencrypt -d tracking.example.com --email you@example.com --agree-tos --no-eff-email
```

Now prepare the app's first-run data and replace the published demo passwords before public
traffic can reach the application. Temporarily set `SESSION_COOKIE_SECURE=0` in `.env`, restart the
service, and open an SSH tunnel from your own computer:

```bash
ssh -L 8000:127.0.0.1:8000 <ssh-user>@<server-ip>
```

With the SSH session open, browse to `http://127.0.0.1:8000`, sign in to each seeded account, and
change each password to a unique strong value. Stop the tunnel, set `SESSION_COOKIE_SECURE=1` in
`.env`, then restart the service:

```bash
sudo systemctl restart parceltrack
```

Install the final HTTPS Nginx site. Replace **every** `tracking.example.com` occurrence with the
hostname covered by the certificate:

```bash
sudo cp /home/parceltrack/parceltrack-lite/deploy/nginx-parceltrack.conf /etc/nginx/sites-available/parceltrack
sudo nano /etc/nginx/sites-available/parceltrack
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status parceltrack --no-pager
```

Check logs if the service does not start:

```bash
sudo journalctl -u parceltrack -n 100 --no-pager
sudo tail -n 100 /home/parceltrack/parceltrack-lite/parceltrack.log
```

### Enable HTTPS and verify the public site

Allow inbound ports 80 and 443 in both the cloud firewall and UFW. The final Nginx configuration
redirects HTTP to HTTPS and serves the application only through TLS. Check automatic renewal and
install a deploy hook so Nginx reloads the renewed certificate:

```bash
sudo certbot renew --dry-run
sudo systemctl enable --now certbot.timer
sudo install -d -m 755 /etc/letsencrypt/renewal-hooks/deploy
printf '#!/bin/sh\nsystemctl reload nginx\n' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx >/dev/null
sudo chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx
```

Verify from a machine outside the VM:

```bash
curl -I http://tracking.example.com
curl -I https://tracking.example.com
```

The HTTP response should redirect to the HTTPS URL; the HTTPS response should be successful. In a
browser, check public tracking, seller registration and parcel listing, rider status/photo update,
and the admin dashboard. Also check that unauthorized parcel access is denied and an unknown URL
shows the generic error page. After HTTPS works, verify `.env` still has `SESSION_COOKIE_SECURE=1`.

### Update after a change is pushed to GitHub

Use this sequence on the VM after the code has been pushed to `main`:

```bash
sudo -u parceltrack git -C /home/parceltrack/parceltrack-lite pull --ff-only origin main
cd /home/parceltrack/parceltrack-lite
sudo -u parceltrack venv/bin/pip install -r requirements.txt
sudo systemctl restart parceltrack
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl status parceltrack --no-pager
```

Then repeat the public browser checks above. Keep `.env`, MySQL data, uploads, and logs when
updating; never run `git clean -fdx` on the server. This update procedure must be exercised once
on the actual server and the HTTPS URL recorded by the task owner before Task 15's live deployment
acceptance can be marked complete.

---

## 2. Daily clean-up of old personal data (Task 16, policy P3)

Policy P3 says we keep a recipient's personal data only while we need it. Twelve months after a
parcel is **Delivered** or **Failed**, the command below:

- replaces the recipient's name, phone and address with `[removed]`
- deletes the parcel's proof-of-delivery photo files from `uploads/`

It keeps the tracking number, status, weight, dates and the status history, so the dashboard
counts and the audit log (P5) still add up. The code is in `app/maintenance.py`.

### Try it first (changes nothing)

```bash
cd /home/parceltrack/parceltrack-lite
venv/bin/flask --app app anonymise-old-parcels --dry-run
```

It prints how many parcels **would** be anonymised. To see what would happen on a future date
(handy for the demo, because the demo parcels are all new):

```bash
venv/bin/flask --app app anonymise-old-parcels --dry-run --as-of 2028-01-01
```

On your own Windows laptop, run them in the project folder with `python -m` in front, because the
`flask` command is often not on the Windows PATH:

```
python -m flask --app app anonymise-old-parcels --dry-run --as-of 2028-01-01
```

### Run it every night with cron

1. On the server, open the cron table:

   ```bash
   crontab -e
   ```

2. Add this one line at the bottom (runs every day at 02:15 server time), then save:

   ```
   15 2 * * * cd /home/parceltrack/parceltrack-lite && venv/bin/flask --app app anonymise-old-parcels >> cron.log 2>&1
   ```

   - `cd` first, so the job finds the `.env` file (database settings) and the `uploads/` folder.
   - `>> cron.log 2>&1` keeps the command's output, so you can check it ran.

3. Check it is saved:

   ```bash
   crontab -l
   ```

### Check that it ran

- `cron.log` gets one line per night, for example `Anonymised 0 parcel(s) and deleted 0 photo(s).`
- `parceltrack.log` gets a matching line: `P3 clean-up: anonymised 0 parcel(s), deleted 0 photo(s)`.
  Only counts are logged, never names, phones, addresses or tracking numbers.

Running it more than once a day is safe: parcels that are already anonymised are skipped.

Both `cron.log` and `parceltrack.log` end in `.log`, so `.gitignore` keeps them off GitHub (P4).
