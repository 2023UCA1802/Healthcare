# Healthcare Backend (Django + DRF + PostgreSQL + JWT)

## Setup

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in .env:
#   SECRET_KEY            python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
#   FIELD_ENCRYPTION_KEYS python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   DB_*                  your Postgres credentials
# create the database first:
#   psql -U postgres -c "CREATE DATABASE healthcare_db;"

python manage.py migrate          # migrations are included in the repo
python manage.py createsuperuser  # optional, for /admin/ (login = email)
python manage.py runserver
```

Run the tests (they use whatever DB your `.env` points at; add `DB_ENGINE=sqlite` for a quick local run):

```bash
python manage.py test
```

Housekeeping (cron daily): `python manage.py flushexpiredtokens` removes expired entries from the token blacklist tables.

## Endpoints

All endpoints except register/login/refresh/logout need `Authorization: Bearer <access_token>`.
List endpoints are paginated: `?page=2&page_size=50` (default 20, max 100) and return `{count, next, previous, results}`.

| Method | URL | Notes |
|---|---|---|
| POST | /api/auth/register/ | `name`, `email`, `password`. Always answers the same 201 (no account discovery) |
| POST | /api/auth/login/ | `email`, `password` -> `access` in the body, **refresh token in an HttpOnly cookie** |
| POST | /api/auth/token/refresh/ | uses the refresh cookie -> new `access` + user; rotates the cookie, blacklists the old token |
| POST | /api/auth/logout/ | blacklists the refresh token, clears the cookie |
| POST/GET | /api/patients/ | GET returns only your (non-deleted) patients |
| GET/PUT/DELETE | /api/patients/<id>/ | owner only (others get 404). DELETE is a **soft delete** |
| POST/GET | /api/doctors/ | your own doctors only |
| GET/PUT/DELETE | /api/doctors/<id>/ | owner only. DELETE returns 409 while the doctor is assigned to a patient |
| POST/GET | /api/mappings/ | GET returns mappings for your patients |
| GET | /api/mappings/<patient_id>/ | doctors assigned to that patient |
| DELETE | /api/mappings/<id>/ | remove a mapping |

## Security design

| Concern | What the code does |
|---|---|
| Brute force | DRF throttles: login 10/min per IP **and** 5/min per email, register 5/hour, refresh 30/min, plus anon 60/min and user 300/min. `NUM_PROXIES=0` so a spoofed `X-Forwarded-For` can't bypass it. Set `REDIS_URL` in production so limits are shared across workers |
| Token theft | Access token is short (15 min) and kept in memory by the frontend. Refresh token is **HttpOnly + SameSite=Strict + Secure(prod)** cookie scoped to `/api/auth/`, rotated on every use, blacklisted after use and on logout. A cookie-authenticated request from an untrusted `Origin` is rejected |
| Account discovery | Register returns an identical response whether or not the email exists; login errors are identical for unknown email / wrong password / disabled account. Doctors are per-user, so doctor emails never leak across users |
| Data at rest | Patient `phone`, `address`, `medical_history` are Fernet-encrypted in the DB (`core/fields.py`). Encrypted columns can't be searched in SQL. Rotate keys by putting the new key **first** in `FIELD_ENCRYPTION_KEYS`. Back the keys up: losing them loses the data |
| Audit trail | `audit.AuditLog` records user, action (LIST/VIEW/CREATE/UPDATE/DELETE, login/logout/failed login), resource id, status code, IP, user agent. It never stores patient data, is append-only, and is read-only in the admin. Also emitted to the `audit` logger |
| Deletion | Patients are soft-deleted; all foreign keys are `PROTECT`, so users/doctors/patients can't be wiped by a cascade |
| Production | With `DEBUG=False`: HTTPS redirect, HSTS, secure cookies (`python manage.py check --deploy` is clean apart from the opt-in `SECURE_HSTS_PRELOAD`). Set `BEHIND_TLS_PROXY=True` if a proxy terminates TLS |
| Custom user | `accounts.User` uses email as the login identifier (case-insensitive unique) |

### Known limits / next steps
- Per-email login throttling can briefly lock a victim out of logging in if someone hammers their email (the usual trade-off vs. credential stuffing).
- No email verification or password reset yet (needs an email provider).
- For HIPAA-style compliance you'd also want: audit-log retention/export, MFA, encrypted backups, and a real key-management service instead of env-var keys.
- The refresh cookie needs the SPA and API on the **same site** (dev: Vite proxy; prod: same domain or reverse proxy).
