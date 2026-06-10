# EatEarn Backend (Django + DRF)

REST API for the EatEarn campus food-ordering app. Django 6, Django REST Framework,
SimpleJWT, and Django's default **SQLite** database (zero external setup).

## Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```

Optional config — copy `.env.example` to `.env` and edit. All values have dev defaults.

## Apps

| App | Models | Responsibility |
|-----|--------|----------------|
| `accounts` | `User` (email login, role, location), `EmailOTP` | Auth, registration, OTP, JWT |
| `catalog` | `Vendor`, `MenuItem` | Cafeterias + menus (with map coordinates) |
| `orders` | `Order`, `OrderItem` | Cart checkout, status flow, delivery coords |
| `notifications` | `Notification` | Per-user / per-role alerts |
| `approvals` | `ApprovalRequest` | Admin approval queue |

## Auth model

- One `User` model for every role (`student` / `vendor` / `delivery` / `admin`),
  using **email** as the username.
- Login is **credentials-only**; the role comes from the account, the client never
  selects it.
- `register` creates an unverified user and issues an OTP. In `DEBUG`, the OTP is
  returned in the response (`devOtp`) and printed to the console so it is testable
  without an SMS gateway. `verify-otp` confirms the account and returns JWT tokens.
- `dev-login` (DEBUG only) logs a demo account in by email without a password —
  convenient for the FYP demo.

## Key endpoints

```
POST /api/auth/register/        {fullName,email,phone,role,password?,...}
POST /api/auth/verify-otp/      {email, code}
POST /api/auth/resend-otp/      {email}
POST /api/auth/login/           {email, password}
POST /api/auth/dev-login/       {email, role?}     (DEBUG only)
GET  /api/auth/me/              (Bearer token)
GET  /api/auth/users/          (admin only)

GET  /api/vendors/
GET  /api/vendors/{id}/menu/
GET  /api/vendors/nearby/?lat=&lng=
GET/POST /api/menu-items/?vendorId=
PATCH /api/menu-items/{id}/toggle/

GET/POST /api/orders/
PATCH /api/orders/{id}/status/  {status}
PATCH /api/orders/{id}/accept/

GET  /api/notifications/
PATCH /api/notifications/{id}/read/
PATCH /api/notifications/read-all/

GET  /api/approvals/
PATCH /api/approvals/{id}/decision/  {status}
```

All list/detail payloads use camelCase keys to match the mobile app's TypeScript types.

## Reset demo data

`python manage.py seed_demo` is idempotent — it clears previously-seeded content and
the four demo accounts, then recreates everything. Other users/superusers are left alone.
