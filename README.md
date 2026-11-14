# SpendWise

A full-stack MCA final-year personal finance application: Next.js App Router + TypeScript, Tailwind, shadcn-style Radix components and Recharts; FastAPI, SQLAlchemy, Alembic and PostgreSQL; Pandas and Scikit-learn analytics.

Use **fictional data only**. SpendWise does not connect to banks, request bank credentials, move money, or execute payments.

## Online deployment

See [Render deployment](docs/DEPLOYMENT.md) for the single-service web deployment
and managed PostgreSQL Blueprint. Free database hosting expires after 30 days.
The deployed database starts empty; local accounts and financial records are not uploaded.

## Quick start: Docker Desktop on Windows

Install Docker Desktop with the WSL2 engine and open this folder in VS Code. In its PowerShell terminal:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec backend python -m app.seed
```

Open [SpendWise](http://localhost:3000), [interactive API docs](http://localhost:8000/docs), or [OpenAPI JSON](http://localhost:8000/openapi.json).

Fictional seeded account: **demo@example.com** / **DemoSpendWise!2026**. Seeding is explicit and skips an existing demo account. New registrations begin empty.

```powershell
docker compose logs -f backend frontend
docker compose exec backend python -m pytest -q
docker compose exec backend alembic current
docker compose down
```

Database data persists in `postgres_data` when containers stop. Avoid `docker compose down -v` unless intentionally erasing the development database. The default database password is for local development only; use a strong URL-safe value before any deployment. Ports bind to loopback.

## Native Windows / VS Code setup

Prerequisites: **Node.js 22 LTS**, **Python 3.12**, **PostgreSQL 16**. Reopen VS Code after installation so PATH is refreshed. VS Code extensions: Python, Pylance, ESLint, and Tailwind CSS IntelliSense are useful.

Create a PostgreSQL role/database using pgAdmin or a PostgreSQL terminal:

```sql
CREATE USER spendwise WITH PASSWORD 'spendwise';
CREATE DATABASE spendwise OWNER spendwise;
```

Backend terminal, starting from the workspace root:

```powershell
cd backend
py -3.12 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Set `DATABASE_URL` in `backend/.env` for your database. Calling the virtual environment's Python directly avoids PowerShell activation-policy changes. Select `backend/.venv/Scripts/python.exe` using VS Code's **Python: Select Interpreter** command.

Frontend terminal:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Frontend requests go through the Next.js `/api/*` rewrite to `API_INTERNAL_URL`. Native default: `http://localhost:8000`; Docker build: `http://backend:8000`. Restart/rebuild Next.js after changing the proxy target. Use `localhost:3000` consistently; if using `127.0.0.1:3000`, add that exact origin to `ALLOWED_ORIGINS` in `backend/.env`.

## Features and semantics

| Area | Implemented behavior |
| --- | --- |
| Authentication | Registration, login, logout, salted scrypt hashes, expiring opaque HttpOnly cookie sessions, hashed session tokens, CSRF tokens, origin checks, process-local auth throttling, authenticated API dependencies |
| Overview | Selected-month income, expenses, net savings, savings rate, cumulative recorded balance through month-end, six-month income/expense chart, category donut, five recent monthly transactions |
| Transactions | Add/edit/delete, fixed categories, description/notes search, date/category/type filters, server pagination, CSV append import and export |
| Budgets | Overall and category monthly limits, edit/delete, actual spending, remaining amounts, progress and overspending notices |
| Subscriptions | Add/edit/delete, monthly/yearly cycles, pause/resume, next renewal, overdue status, upcoming count and monthly equivalent cost |
| Insights | Explainable merchant keyword categorization, 90-day category/average spending analysis, Isolation Forest unusual-amount flags |
| Forecast | 30-day recorded-balance projection, 14-day history requirement, daily linear model, approximate 80% residual uncertainty band, explicit limitations |
| Reports | Selected-month totals, category breakdown, CSV summary download |
| Settings | Profile name, display currency (INR default), persisted in-app notification preference, sign out |

Subscriptions are reminders: payments do **not** automatically create transactions or advance renewal dates. Edit next renewal after recording a payment. Notifications are in-app only; email, push delivery, and background jobs are not implemented. Overall and category budgets overlap and are not summed. Changing display currency **does not convert amounts**; use one currency consistently. Balance means recorded income minus recorded expenses, not a bank account balance. Future-dated transactions appear in selected-month totals; forecasting uses history only through today.

### CSV

Use UTF-8 CSV; ISO `YYYY-MM-DD` dates; positive amounts with at most two decimal places; `income` or `expense` kinds; exact category names from `/categories`. Example: [examples/transactions.csv](examples/transactions.csv).

```csv
title,amount,kind,category,date,notes
Fictional salary,85000,income,Salary,2026-11-01,Academic demo
Corner Cafe,320.50,expense,Food & Dining,2026-11-02,Fictional purchase
```

Imports are atomic: an invalid row prevents the entire upload. Limit: 2 MB / 5,000 rows. Re-importing appends duplicates. Export applies date filters and includes all transaction types/categories. Text beginning with spreadsheet formula characters is prefixed with an apostrophe for safe viewing; exported formula-like descriptions therefore do not round-trip byte-for-byte.

## Architecture

```text
frontend/
  app/                    App Router pages, layout, error/loading boundaries
  components/spendwise.tsx Authenticated workspace, pages and forms
  components/ui/          shadcn-style Button and accessible Radix Dialog
  lib/                    API client, shared types and utilities
backend/
  app/config.py           Environment configuration
  app/database.py         Engine and request-scoped database sessions
  app/models.py           User, Session, Transaction, Budget, Subscription
  app/schemas.py          Pydantic validation
  app/security.py         Password hashing, sessions, CSRF and identity
  app/main.py             API routes, ownership checks, aggregations, CSV
  app/analytics.py        Pandas/Scikit-learn insights and forecast
  app/seed.py             Explicit deterministic fictional seed
  migrations/             Versioned Alembic PostgreSQL schema
  tests/                  Isolated SQLite API integration suite
```

Every financial query is scoped to the session owner. Decimal values use `NUMERIC(14,2)`; responses may serialize amounts as strings. Financial totals are computed with Decimal; chart/model calculations use floats. Database schema changes run through Alembic, never automatic `create_all` at application startup.

## Checks

```powershell
# From backend, using your virtual environment
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check

# From frontend
npm run typecheck
npm run build
npm audit
```

Tests use a separate in-memory SQLite database per test and never touch your PostgreSQL data. PostgreSQL-specific SQL/constraints and container startup must also be validated with the Docker workflow. [VERIFICATION.md](VERIFICATION.md) records the actual checks performed in this workspace, including environment limits.

## Security and deployment boundaries

For HTTPS deployments set `COOKIE_SECURE=true`, restrict `ALLOWED_ORIGINS`, set strong database credentials, and place services behind a TLS reverse proxy. The in-process limiter allows 20 authentication attempts per client IP per minute; add a shared gateway/Redis limiter for multiple workers. It trusts the direct connection address rather than arbitrary forwarded headers; behind Next.js this may rate-limit the shared proxy address. API data requires authentication even though the frontend sign-in gate renders client-side.

This academic application has no password recovery, email verification, MFA, bank integrations, currency conversion, automatic recurring ledger posting, or calibrated financial-risk model. Do not expose the seeded demo account or use real financial data in a public deployment. Forecast intervals assume independent residuals, omit parameter uncertainty and cannot predict shocks or unrecorded bills. Irregular salary timing can substantially distort a linear daily model.

## API documentation

See [docs/API.md](docs/API.md). FastAPI provides generated request/response schemas at `/docs` and `/redoc`. For mutations, first log in, retain the session cookie, and send the returned `csrf` value in `X-CSRF-Token`.
