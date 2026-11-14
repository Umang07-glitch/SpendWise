import csv
import io
import time
from collections import defaultdict, deque
from datetime import date, timedelta
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from .config import settings
from .database import get_db
from .models import User, Transaction, Budget, Subscription
from .schemas import Register, Login, Profile, TransactionIn, TransactionOut, BudgetIn, SubscriptionIn, CATEGORIES
from .security import current_user, hash_password, verify_password, create_session, public_user
from .analytics import categorize, insights, forecast

app = FastAPI(title="SpendWise API", version="1.0.0", description="Personal finance API. Authenticate with session cookies; obtain CSRF from /auth/me and send X-CSRF-Token on mutations.")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins.split(","), allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])
auth_attempts = defaultdict(deque)


@app.middleware("http")
async def headers(request: Request, call_next):
    from fastapi.responses import JSONResponse
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins.split(","):
            return JSONResponse(status_code=403, content={"detail": "Untrusted request origin"})
    if request.url.path in ("/auth/login", "/auth/register") and request.method == "POST":
        now = time.monotonic()
        # Bound memory and ignore untrusted forwarded headers. Production deployments
        # should additionally enforce a shared limiter at the trusted reverse proxy.
        for key in list(auth_attempts):
            if not auth_attempts[key] or now - auth_attempts[key][-1] > 60:
                del auth_attempts[key]
        key = request.client.host if request.client else "unknown"
        attempts = auth_attempts[key]
        while attempts and now-attempts[0] > 60:
            attempts.popleft()
        if len(attempts) >= 20:
            return JSONResponse(status_code=429, content={"detail": "Too many sign-in attempts. Try again in a minute."}, headers={"Retry-After": "60"})
        attempts.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": "A record with these details already exists."})


@app.get("/health")
def health(db: DBSession = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/auth/register", status_code=201)
def register(data: Register, response: Response, db: DBSession = Depends(get_db)):
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email is already registered")
    user = User(email=email, name=data.name.strip(), password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return create_session(db, user, response)


@app.post("/auth/login")
def login(data: Login, response: Response, db: DBSession = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    # Always run a password derivation, including unknown accounts.
    valid = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Invalid email or password")
    return create_session(db, user, response)


DUMMY_HASH = hash_password("dummy-not-a-user-password")


@app.get("/auth/me")
def me(request: Request, user=Depends(current_user)):
    return {"user": public_user(user), "csrf": request.state.session.csrf}


@app.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user=Depends(current_user), db: DBSession = Depends(get_db)):
    db.delete(request.state.session)
    db.commit()
    response.delete_cookie("spendwise_session", path="/")


@app.patch("/profile")
def profile(data: Profile, user=Depends(current_user), db: DBSession = Depends(get_db)):
    for key, value in data.model_dump().items():
        setattr(user, key, value)
    db.commit()
    return public_user(user)


@app.get("/categories")
def categories(user=Depends(current_user)):
    return CATEGORIES


def owned(db, model, record_id, user):
    record = db.scalar(select(model).where(model.id == record_id, model.user_id == user.id))
    if not record:
        raise HTTPException(404, "Record not found")
    return record


def tx_query(user, search="", category=None, kind=None, start=None, end=None):
    q = select(Transaction).where(Transaction.user_id == user.id)
    if search:
        q = q.where(or_(Transaction.title.ilike(f"%{search}%"), Transaction.notes.ilike(f"%{search}%")))
    if category:
        q = q.where(Transaction.category == category)
    if kind:
        q = q.where(Transaction.kind == kind)
    if start:
        q = q.where(Transaction.date >= start)
    if end:
        q = q.where(Transaction.date <= end)
    return q


@app.get("/transactions")
def transactions(search: str = Query("", max_length=160), category: str | None = None, kind: str | None = None, start: date | None = None, end: date | None = None, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), user=Depends(current_user), db: DBSession = Depends(get_db)):
    q = tx_query(user, search, category, kind, start, end)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Transaction.date.desc(), Transaction.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items": [TransactionOut.model_validate(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@app.post("/transactions", status_code=201, response_model=TransactionOut)
def add_transaction(data: TransactionIn, user=Depends(current_user), db: DBSession = Depends(get_db)):
    row = Transaction(user_id=user.id, **data.model_dump())
    db.add(row)
    db.commit()
    return row


@app.put("/transactions/{record_id}", response_model=TransactionOut)
def edit_transaction(record_id: int, data: TransactionIn, user=Depends(current_user), db: DBSession = Depends(get_db)):
    row = owned(db, Transaction, record_id, user)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return row


@app.delete("/transactions/{record_id}", status_code=204)
def delete_transaction(record_id: int, user=Depends(current_user), db: DBSession = Depends(get_db)):
    db.delete(owned(db, Transaction, record_id, user))
    db.commit()


def csv_response(rows, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        # Prevent formula execution when downloaded CSV is opened in spreadsheet apps.
        writer.writerow([("'" + v) if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v for v in row])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/export/transactions")
def export_transactions(start: date | None = None, end: date | None = None, user=Depends(current_user), db: DBSession = Depends(get_db)):
    rows = db.scalars(tx_query(user, start=start, end=end).order_by(Transaction.date)).all()
    return csv_response([["title", "amount", "kind", "category", "date", "notes"], *[[r.title, str(r.amount), r.kind, r.category, str(r.date), r.notes] for r in rows]], "spendwise-transactions.csv")


@app.post("/import/transactions")
async def import_transactions(file: UploadFile = File(...), user=Depends(current_user), db: DBSession = Depends(get_db)):
    raw = await file.read(2_000_001)
    if len(raw) > 2_000_000:
        raise HTTPException(413, "CSV must be smaller than 2 MB")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        required = {"title", "amount", "kind", "category", "date"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Required columns: title, amount, kind, category, date; optional notes")
        parsed = []
        for line, row in enumerate(reader, 2):
            if line > 5001:
                raise ValueError("Maximum 5,000 rows per import")
            try:
                parsed.append(TransactionIn.model_validate(row))
            except ValueError:
                raise ValueError(f"Invalid CSV row {line}; check amount, kind, category and ISO date")
        if not parsed:
            raise ValueError("CSV contains no transactions")
    except (ValueError, UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(422, str(exc))
    db.add_all([Transaction(user_id=user.id, **r.model_dump()) for r in parsed])
    db.commit()
    return {"imported": len(parsed), "warning": "Imports append rows; repeated uploads create duplicates."}


def month_bounds(month):
    try:
        start = date.fromisoformat(month + "-01")
    except ValueError:
        raise HTTPException(422, "Month must be YYYY-MM")
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, end


@app.get("/budgets")
def budgets(month: str, user=Depends(current_user), db: DBSession = Depends(get_db)):
    start, end = month_bounds(month)
    rows = db.scalars(select(Budget).where(Budget.user_id == user.id, Budget.month == month)).all()
    expenses = db.scalars(tx_query(user, kind="expense", start=start, end=end-timedelta(days=1))).all()
    result = []
    for r in rows:
        spent = sum((t.amount for t in expenses if r.category == "All" or t.category == r.category), Decimal(0))
        result.append({"id": r.id, "month": r.month, "category": r.category, "amount": r.amount, "spent": spent, "remaining": r.amount-spent, "overspent": spent > r.amount})
    return result


@app.post("/budgets", status_code=201)
def add_budget(data: BudgetIn, user=Depends(current_user), db: DBSession = Depends(get_db)):
    month_bounds(data.month)
    row = Budget(user_id=user.id, **data.model_dump())
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.put("/budgets/{record_id}")
def edit_budget(record_id: int, data: BudgetIn, user=Depends(current_user), db: DBSession = Depends(get_db)):
    month_bounds(data.month)
    row = owned(db, Budget, record_id, user)
    for k, v in data.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return {"id": row.id}


@app.delete("/budgets/{record_id}", status_code=204)
def delete_budget(record_id: int, user=Depends(current_user), db: DBSession = Depends(get_db)):
    db.delete(owned(db, Budget, record_id, user))
    db.commit()


@app.get("/subscriptions")
def subscriptions(user=Depends(current_user), db: DBSession = Depends(get_db)):
    rows = db.scalars(select(Subscription).where(Subscription.user_id == user.id).order_by(Subscription.next_due)).all()
    return {"items": [{"id": r.id, "name": r.name, "amount": r.amount, "cycle": r.cycle, "next_due": r.next_due, "category": r.category, "active": r.active} for r in rows], "monthly_cost": sum((r.amount / (12 if r.cycle == "yearly" else 1) for r in rows if r.active), Decimal(0))}


@app.post("/subscriptions", status_code=201)
def add_subscription(data: SubscriptionIn, user=Depends(current_user), db: DBSession = Depends(get_db)):
    row = Subscription(user_id=user.id, **data.model_dump())
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.put("/subscriptions/{record_id}")
def edit_subscription(record_id: int, data: SubscriptionIn, user=Depends(current_user), db: DBSession = Depends(get_db)):
    row = owned(db, Subscription, record_id, user)
    for k, v in data.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return {"id": row.id}


@app.delete("/subscriptions/{record_id}", status_code=204)
def delete_subscription(record_id: int, user=Depends(current_user), db: DBSession = Depends(get_db)):
    db.delete(owned(db, Subscription, record_id, user))
    db.commit()


@app.get("/dashboard")
def dashboard(month: str, user=Depends(current_user), db: DBSession = Depends(get_db)):
    start, end = month_bounds(month)
    rows = db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.date < end)).all()
    current = [r for r in rows if r.date >= start]
    income = sum((r.amount for r in current if r.kind == "income"), Decimal(0))
    expenses = sum((r.amount for r in current if r.kind == "expense"), Decimal(0))
    balance = sum((r.amount * (1 if r.kind == "income" else -1) for r in rows), Decimal(0))
    trends = []
    for offset in range(5, -1, -1):
        index = start.year*12 + start.month-1-offset
        key = f"{index//12:04d}-{index%12+1:02d}"
        subset = [r for r in rows if str(r.date).startswith(key)]
        trends.append({"month": key, "income": sum((r.amount for r in subset if r.kind == "income"), Decimal(0)), "expenses": sum((r.amount for r in subset if r.kind == "expense"), Decimal(0))})
    breakdown = {}
    for r in current:
        if r.kind == "expense":
            breakdown[r.category] = breakdown.get(r.category, Decimal(0)) + r.amount
    return {"income": income, "expenses": expenses, "savings": income-expenses, "balance": balance, "savings_rate": round(float((income-expenses)/income*100), 1) if income else 0, "trends": trends, "categories": [{"name": k, "value": v} for k, v in sorted(breakdown.items(), key=lambda item: item[1], reverse=True)], "recent": [TransactionOut.model_validate(r) for r in sorted(current, key=lambda r: (r.date, r.id), reverse=True)[:5]]}


@app.get("/reports")
def reports(month: str, user=Depends(current_user), db: DBSession = Depends(get_db)):
    return dashboard(month, user, db)


@app.get("/export/report")
def export_report(month: str, user=Depends(current_user), db: DBSession = Depends(get_db)):
    data = dashboard(month, user, db)
    return csv_response([["Month", "Metric", "Amount", "Currency"], *[[month, key, data[key], user.currency] for key in ("income", "expenses", "savings", "balance")], *[[month, r["name"], r["value"], user.currency] for r in data["categories"]]], f"spendwise-{month}.csv")


@app.get("/insights")
def get_insights(user=Depends(current_user), db: DBSession = Depends(get_db)):
    rows = db.scalars(tx_query(user, start=date.today()-timedelta(days=89), end=date.today())).all()
    return insights(rows)


@app.get("/categorize")
def get_category(title: str = Query(min_length=1, max_length=160), user=Depends(current_user)):
    return categorize(title)


@app.get("/forecast")
def get_forecast(user=Depends(current_user), db: DBSession = Depends(get_db)):
    return forecast(db.scalars(tx_query(user)).all())
