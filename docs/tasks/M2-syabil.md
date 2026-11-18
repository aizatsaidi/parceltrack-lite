# M2 · Parcel Registration and Public Tracking · Syabil

Policies: **P1, P3, P4** · Folder: `app/parcels/`, `app/templates/parcels/` · Tests: `tests/test_m2.py`

## Already working

- Seller registers a parcel with server-side validation of phone, address and weight
  (`/seller/parcels/new`)
- Tracking number made with Python `secrets` (10 random characters, unique)
- Seller list and search shows only their own parcels (`/seller/parcels`)
- Public tracking page shows status, date and time only (`/track`)

## To do (one item at a time)

1. **Rate limit on tracking lookups** (stops attackers guessing tracking numbers).
   For example, at most 20 lookups per minute per IP address with `Flask-Limiter`,
   added to `requirements.txt`. Over the limit, show a generic "Too many requests,
   try again later" page (HTTP 429).
2. **Seller parcel detail page** `/seller/parcels/<id>` showing one parcel and its status
   history. The server must check `parcel.seller_id == current_user.id` and return 403
   otherwise. This is what the rubric's "changing a parcel ID in the URL" test checks.
3. **Tidy validation messages** so every rejected input gets a short, clear message and
   nothing technical is shown (P4).
4. **Tests** in `tests/test_m2.py`, at least 6 input types.

## Rubric key controls (criterion 2a)

Parameterised queries · output encoding against XSS · ownership checked on the server for
every parcel ID · cryptographically random tracking number · server-side validation ·
tracking page never shows name, phone or address · rate limit on lookups.

## Rubric suggested tests (criterion 3)

| Input | Expected result |
|---|---|
| `' OR '1'='1` in the parcel search | No other sellers' parcels; no error |
| `<script>alert(1)</script>` in the address | Shown as plain text; no pop-up |
| Phone `abc` or weight `-2` | Rejected with a clear message |
| Seller opens another seller's `/seller/parcels/<id>` | 403 |
| Made-up or sequential tracking number such as `RX-0000000001` | "No parcel found"; no details leaked |
| 25 tracking lookups in one minute | Blocked after the limit (429) |

## Things to be ready to explain in the demo

Why `secrets` instead of `random` or an auto-increment number; how the ORM prevents SQL
injection; why Jinja escaping stops XSS; why the public page never shows personal data
(P3); how the rate limit stops guessing.
