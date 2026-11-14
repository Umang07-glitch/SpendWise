# SpendWise API

Base URL: `http://localhost:8000` (browser proxy: `http://localhost:3000/api`). Interactive OpenAPI documentation: `/docs`; ReDoc: `/redoc`; machine-readable schema: `/openapi.json`.

Authentication uses an HttpOnly `spendwise_session` cookie. Register/login returns `{user, csrf}`. `GET /auth/me` refreshes identity and retrieves the session's CSRF token. All authenticated mutations require `X-CSRF-Token`. Mutation Origin, when supplied, must match `ALLOWED_ORIGINS`. Authentication attempts are limited to 20/minute/IP/process.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Database connectivity |
| POST | `/auth/register` | `{name,email,password}`; password 10–128 characters |
| POST | `/auth/login` | `{email,password}` |
| GET | `/auth/me` | Current public profile and CSRF token |
| POST | `/auth/logout` | Revoke current session; 204 |
| PATCH | `/profile` | `{name,currency,notifications}` |
| GET | `/categories` | Allowed fixed category strings |
| GET | `/transactions` | `search,category,kind,start,end,page,page_size` |
| POST | `/transactions` | Create; 201 |
| PUT | `/transactions/{id}` | Full replacement of editable fields |
| DELETE | `/transactions/{id}` | Owner-scoped deletion; 204 |
| POST | `/import/transactions` | Multipart `file`; atomic CSV append |
| GET | `/export/transactions` | CSV; optional `start,end` |
| GET | `/dashboard` | Required `month=YYYY-MM`; totals, six-month trends, categories and recent records |
| GET | `/budgets` | Required `month`; includes spending, remaining, overspent |
| POST | `/budgets` | `{month,category,amount}`; category may be `All` |
| PUT | `/budgets/{id}` | Update monthly/category budget |
| DELETE | `/budgets/{id}` | Delete; 204 |
| GET | `/subscriptions` | Items and monthly equivalent active cost |
| POST | `/subscriptions` | Create recurring reminder |
| PUT | `/subscriptions/{id}` | Update reminder or active status |
| DELETE | `/subscriptions/{id}` | Delete; 204 |
| GET | `/categorize` | Required `title`; suggestion, method and explanation |
| GET | `/insights` | Last 90 days of expense patterns and unusual amounts |
| GET | `/forecast` | 30 points and uncertainty/limitations, or `insufficient_data` |
| GET | `/reports` | Required `month`; monthly dashboard aggregates |
| GET | `/export/report` | Required `month`; summary/category CSV |

Transaction body:

```json
{"title":"Corner Cafe","amount":"320.50","kind":"expense","category":"Food & Dining","date":"2026-11-02","notes":"Fictional example"}
```

Subscription body:

```json
{"name":"Fictional Music","amount":"119.00","cycle":"monthly","next_due":"2026-12-01","category":"Entertainment","active":true}
```

Pagination starts at 1; `page_size` defaults to 10 and is capped at 100. Responses contain `items,total,page,page_size`. Money has up to 12 integral and two fractional digits and must be positive. Categories must exactly match `/categories`. No implicit FX conversion occurs.

Errors use `{"detail":"message"}` or FastAPI's structured validation detail array. Status codes: 401 unauthenticated/invalid credentials; 403 invalid CSRF/origin; 404 inaccessible/missing owned record; 409 duplicate email or budget; 413 oversized CSV; 422 invalid input; 429 authentication throttle. No other user's record is disclosed through a 404 response.
