# Verification record

Executed in the Windows workspace on 14 November 2026.

## Passed

- Downloaded official workspace-local Node.js 22.16.0, npm 10.9.2 and Python 3.12.10, since the host had no Node/Python/Docker on PATH. Tools and dependency caches are ignored under `.tools/`.
- Installed frontend and backend dependencies. Added the npm lockfile for repeatable `npm ci` installs.
- TypeScript `tsc --noEmit`: passed.
- Next.js **15.5.29** production build: passed with React **19.1.6**, Recharts **3.10.1**, and Tailwind **3.4.17**. Includes root and all dynamic workspace routes.
- `npm audit`: **0 reported vulnerabilities**, after patching Next.js and overriding its PostCSS/Sharp transitive versions. Advisory results are time-dependent and do not establish complete application security.
- `pytest -q`: **8 passed**. One third-party Starlette/AnyIO deprecation warning; no failures.
- Alembic `upgrade head`: executed against an isolated on-disk SQLite verification database.
- Alembic `check`: **No new upgrade operations detected**, against the SQLite verification database.
- Alembic PostgreSQL offline SQL generation: passed, including numeric fields, ownership foreign keys, constraints and indexes. This checks SQL generation only.
- Fictional seed command: succeeded; a second run skipped the existing account as intended.
- Docker Compose YAML: parsed and required three services found. This is a static check, not a Docker execution.
- `scripts/smoke.py` against the running **production-built frontend** and real FastAPI process through the Next.js proxy: passed. Checked eight frontend route HTTP responses, unauthenticated rejection, login/cookie persistence, eleven authenticated API reads (including insights/forecast and CSV exports), transaction creation/update/deletion, logout and session rejection afterward. Used only the local fictional SQLite database.

## API integration coverage

| Test | Verified behaviors |
| --- | --- |
| Password hashing | Distinct salts, correct password accepted, wrong password rejected |
| Authentication throttling/origin | Foreign Origin denied, 20 attempts/minute cap, 429/Retry-After |
| Authentication lifecycle | Registration, safe public user fields, HttpOnly/SameSite cookie, missing CSRF denied, logout revokes session, valid/invalid login, duplicate email |
| Transactions | Create/update/delete, search/category/type filters, pagination input validation, invalid amount/precision/date/kind/category rejected |
| User isolation | Second account cannot list/export first account's records or modify/delete its transactions/budgets/subscriptions |
| Dashboard/reports/budgets | Exact selected-month totals, savings rate, six-month output, monthly/category budget accounting, duplicate conflict, overspending/remaining, update/delete, CSV report |
| CSV | Invalid row prevents whole import, valid import succeeds, missing columns rejected, spreadsheet formula prefix sanitized |
| Subscriptions/profile/analytics | Annual-to-monthly equivalent, inactive exclusion, update/delete, profile currency validation, keyword and fallback categorization, anomaly output on varied data, 30-day forecast with ordered uncertainty bounds |

## Not verified here

- **Live PostgreSQL migrations, runtime queries and Docker image/container startup**: PostgreSQL and Docker are not installed. Docker Compose and a PostgreSQL-backed CI workflow are supplied, but neither was executed here. SQLite passing does not prove PostgreSQL behavior.
- **Browser rendering, interaction, responsiveness and accessibility**: browser preview creation failed with `The browser access host is unavailable`; browser inventory confirmed the same infrastructure error. No screenshots, mobile visual checks or browser-level end-to-end tests were performed. Route HTTP checks and builds do not substitute for these checks.
- **Backend advisory audit**: `pip-audit` could not start because the embeddable Python distribution lacks `venv`. The fallback network advisory check was declined and was not performed. Backend packages are pinned but are not certified free of known vulnerabilities.
- CI workflow has been authored, not run on GitHub.
- No external financial data, bank credentials, payments, email or push delivery were used or tested.

## Repeat locally

Follow the Docker or native PostgreSQL setup in [README.md](README.md), run backend tests and migrations, then frontend typecheck/build. With both services running and the fictional account seeded:

```powershell
# From root using the backend virtual environment
.\backend\.venv\Scripts\python.exe scripts/smoke.py
```

The smoke script creates and removes one explicitly fictional transaction. It is intended only for local development. Review all eight UI pages at desktop and mobile widths before presenting or deploying the project.
