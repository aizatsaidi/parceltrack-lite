# Deploying ParcelTrack Lite

## 1. Server setup (Task 15, Syabil)

_To be written in Task 15: creating the server, installing Python and MySQL, the `.env` file,
running the app behind a web server with HTTPS, and how to update the server after new pushes._

The steps below assume the project is in `/home/ubuntu/parceltrack-lite` with its virtual
environment in `venv/`. Change the paths if the server uses different ones.

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
cd /home/ubuntu/parceltrack-lite
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
   15 2 * * * cd /home/ubuntu/parceltrack-lite && venv/bin/flask --app app anonymise-old-parcels >> cron.log 2>&1
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
