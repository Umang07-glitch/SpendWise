# Host SpendWise on Render

The root `Dockerfile` builds Next.js and runs its standalone server beside FastAPI.
Only Next.js listens publicly. `/api/*` forwards to FastAPI on loopback port 8000.
PostgreSQL is a separate managed database. Migrations run before the servers start.
If either server exits, the supervisor stops the other and exits unsuccessfully.

## Deploy

1. Sign in to [Render](https://dashboard.render.com/) with GitHub.
2. Choose **New > Blueprint** and connect `Umang07-glitch/SpendWise`.
3. Use `render.yaml` on branch `main`. Review the resources: one **Free** web
   service and one **Free** PostgreSQL database in Singapore.
4. Create the Blueprint. Do not choose a paid plan unless you intend to pay.
5. Wait for the database and application deployment to become healthy. Open the
   exact HTTPS URL shown by Render and register a new account.

There is no automatically seeded account and no copy of your local database.
The login session uses a Secure, HttpOnly cookie. Render supplies the external
HTTPS origin through `RENDER_EXTERNAL_URL`; the app uses it for origin checks.
If you add a custom domain, set `ALLOWED_ORIGINS` to the exact comma-separated
HTTPS origins you use, without trailing slashes, then redeploy.

The database password stays in Render's environment variables. The Blueprint
blocks public database connections. Never paste the connection string into a
GitHub file or commit a local `.env`.

## Verify before sharing

- `/api/health` returns `{"status":"ok"}`; Render also checks this route.
- Register, log out, and log in again over HTTPS.
- Add a fictional transaction, edit it, refresh, and check dashboard/report totals.
- Register a second account and confirm the first account's records are hidden.
- Restart/redeploy the web service and confirm data remains in PostgreSQL.

## Free plan limits

[Render's free hosting](https://render.com/docs/free) spins down after 15 minutes
without traffic, and waking can take about a minute. Free PostgreSQL expires
after 30 days, has no backups, and is limited to one active free database per
workspace. Export CSV reports before expiry; this configuration is for a college
demo rather than permanent storage. Review account usage/spend limits, especially
if you have added a payment method. No paid upgrade is performed by this project.

The free service has limited memory shared by Next.js and the analytics backend.
Concurrent large imports or analytics requests may exceed that limit; check logs
before considering an explicitly approved larger plan. The in-memory login
limiter is suitable for this single instance; larger deployments need shared
rate limiting at a trusted proxy.

## Verification boundary

Local tests/builds do not prove that Render's Docker build, PostgreSQL migration,
HTTPS cookie proxying, or live service have succeeded. Confirm deployment status
and the live checks above before announcing a working URL.
