# SocietyHub — Apartment Society Management

A secure, **API-first** society management web application built with **FastAPI**.
Because the core is a clean REST API (JWT-secured), the same backend can later power
**Android/iOS** apps without changes. A responsive web frontend (Bootstrap) is bundled.

## Features

### Three login roles
| Role | How they join | What they can do |
|------|---------------|------------------|
| **IT Support** (super admin) | Seeded automatically | Full control: approve managers, create/edit departments, assign managers to departments, manage all users, post transactions & broadcasts |
| **Society Manager** | Signup with mobile + **OTP** → must be **approved by IT Support** | Add credit/debit entries (with item, amount, source of money, comment) for their **assigned departments**, post society broadcasts |
| **Flat Member** | Signup with mobile + **flat no** + **OTP** (only **one registration per flat**) | Read-only view of credit/debit and society updates/broadcasts |

### Core capabilities
- **Mobile OTP** verification for signup & optional OTP login (real SMS via Twilio or MSG91; console mode for development).
- **Departments** created by IT Support. Ships with **default departments** derived from the maintenance expense sheet (Security, Housekeeping, Electricity, STP, Plumber, Gardener, Electrician, Pest Control, Diesel for DG, Garbage Collection, materials, DG AMC, Lift AMC, Gym, CCTV, Fire Safety, Maintenance Collection, Water Tanker, Miscellaneous…).
- **Credit / Debit ledger** per department with item/purpose, amount, source of funds, and comments.
- **Broadcasts** — managers & IT Support publish society-wide updates.
- **Dashboard** — society-wide and per-department credit/debit/balance totals, recent activity.

### Security (OWASP-aware)
- Passwords hashed with **bcrypt**; JWT access tokens (`python-jose`).
- OTPs stored **hashed**, short expiry, attempt limits, and resend cooldown.
- **Role-based access control** enforced server-side on every write.
- Input validation via Pydantic; ORM (SQLAlchemy) prevents SQL injection.
- Secrets loaded from `.env` (never committed).

## Project structure
```
backend/
  app/
    main.py            # FastAPI app + static frontend hosting
    config.py          # env-driven settings
    database.py        # SQLAlchemy engine/session
    models.py          # User, Department, Transaction, Broadcast, OtpCode
    schemas.py         # Pydantic request/response models
    security.py        # hashing, JWT, OTP
    sms.py             # console / Twilio / MSG91 providers
    deps.py            # auth & role dependencies
    seed.py            # default admin + departments
    routers/           # auth, users, departments, transactions, broadcasts, dashboard
  frontend/            # Bootstrap SPA (index.html, css, js)
  requirements.txt
  .env.example
```

## Getting started

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then edit .env (set SECRET_KEY, admin creds, SMS keys)
uvicorn app.main:app --reload
```

Then open:
- Web app: <http://localhost:8000/>
- API docs (Swagger): <http://localhost:8000/docs>

### Default IT Support login
Configured in `.env` (`DEFAULT_ADMIN_MOBILE` / `DEFAULT_ADMIN_PASSWORD`).
Defaults: mobile `+919999999999`, password `ChangeMe@123` — **change these**.

### OTP in development
With `SMS_PROVIDER=console` (default), OTPs are printed to the **server console**
(and returned in logs) instead of being sent by SMS. Set `SMS_PROVIDER=twilio` or
`msg91` and fill the matching keys in `.env` to send real SMS.

## Typical flow
1. Log in as **IT Support** → review default departments, create more if needed.
2. A **Manager** signs up (mobile + OTP) → appears under **Users → Pending Managers**.
3. IT Support **approves** the manager and **assigns departments**.
4. Manager logs in → adds **credit/debit** entries and **broadcasts**.
5. **Members** sign up (mobile + flat no + OTP, one per flat) → view ledger & updates.

## Porting to mobile later
The REST API under `/api/*` (see `/docs`) is the single source of truth. An Android
(Kotlin/Flutter) or iOS (Swift/Flutter) app authenticates via `/api/auth/login`
(or `/api/auth/login-otp`), stores the JWT, and consumes the same endpoints.
Swap `DATABASE_URL` to PostgreSQL for production with no code changes.
