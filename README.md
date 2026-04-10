# iTalkVoIP Admin Backend

This repository now runs on Django and Django REST Framework. It keeps the same mobile onboarding API shape from the old service, but the admin side is now built properly with Django admin at `/admin/`.

## Stack

- Python 3.12+
- Django 5
- Django REST Framework
- SQLite for local development

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_initial_data
python manage.py runserver 0.0.0.0:3000
```

## Main Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/register/resend-otp`
- `POST /api/v1/auth/verify-registration`
- `POST /api/v1/auth/login/request-otp`
- `POST /api/v1/auth/login/resend-otp`
- `POST /api/v1/auth/login/verify-otp`
- `POST /api/v1/auth/admin/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/domains`
- `POST /api/v1/onboarding/domain`
- `GET /api/v1/onboarding/extension`
- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/domains`
- `POST /api/v1/admin/domains`
- `PATCH /api/v1/admin/domains/<id>`
- `GET /api/v1/admin/users`

## Admin

Use Django admin at `http://localhost:3000/admin/`.

The seeded admin login comes from:

- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

## Notes

- OTP emails use SMTP when configured.
- If SMTP is not configured, OTP emails go to Django's console email backend for development.
- `python manage.py seed_initial_data` creates the initial admin and starter domains.
