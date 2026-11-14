from datetime import date, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression


def categorize(title: str):
    text = title.lower()
    rules = {"Food & Dining": ["cafe", "restaurant", "grocery", "swiggy", "zomato"], "Transport": ["uber", "metro", "petrol", "ola"], "Shopping": ["amazon", "store", "flipkart"], "Housing": ["rent"], "Salary": ["salary", "payroll"], "Entertainment": ["netflix", "spotify", "cinema"], "Utilities": ["electricity", "internet", "water"]}
    for category, words in rules.items():
        if any(word in text for word in words):
            return {"category": category, "method": "keyword rule", "explanation": "Matched a merchant or description keyword. Review before saving."}
    return {"category": "Other", "method": "fallback", "explanation": "No matching keyword. Choose a category manually."}


def insights(rows):
    expenses = [r for r in rows if r.kind == "expense"]
    messages, unusual = [], []
    if not expenses:
        return {"messages": ["Add expenses to unlock spending insights."], "unusual": [], "method": "Isolation Forest; exploratory signals, not fraud decisions."}
    df = pd.DataFrame([{"id": r.id, "amount": float(r.amount), "category": r.category, "title": r.title} for r in expenses])
    grouped = df.groupby("category").amount.sum().sort_values(ascending=False)
    messages.append(f"{grouped.index[0]} accounts for {grouped.iloc[0] / grouped.sum():.0%} of recorded expenses.")
    messages.append(f"Your average recorded expense is {df.amount.mean():.2f} across {len(df)} transactions.")
    if len(df) >= 12 and df.amount.nunique() > 1:
        model = IsolationForest(contamination=0.08, random_state=42)
        labels = model.fit_predict(np.log1p(df[["amount"]]))
        unusual = df[labels == -1].sort_values("amount", ascending=False).head(5).to_dict("records")
    else:
        messages.append("At least 12 varied expenses are needed for unusual-amount detection.")
    return {"messages": messages, "unusual": unusual, "method": "Isolation Forest on log transaction amounts (8% contamination). Flags can include legitimate purchases and small amounts; no fraud classification."}


def forecast(rows):
    today = date.today()
    rows = [r for r in rows if r.date <= today]
    balance = sum(float(r.amount) * (1 if r.kind == "income" else -1) for r in rows)
    limitations = ["An illustrative statistical estimate, not financial advice or a guarantee.", "Only recorded transactions are included; external account balances and future unrecorded bills are unknown.", "The band is an approximate 80% residual interval, not a calibrated probability guarantee. Irregular income can make forecasts unreliable."]
    if not rows or (today - min(r.date for r in rows)).days < 14:
        return {"status": "insufficient_data", "points": [], "limitations": limitations + ["Record at least 14 days of history to generate a forecast."], "history_days": 0}
    start = max(min(r.date for r in rows), today - timedelta(days=179))
    series = pd.Series(0.0, index=pd.date_range(start, today))
    for r in rows:
        if r.date >= start:
            series[pd.Timestamp(r.date)] += float(r.amount) * (1 if r.kind == "income" else -1)
    x = np.arange(len(series)).reshape(-1, 1)
    # Zero-activity days remain in the daily model so missing days do not inflate flow.
    model = LinearRegression().fit(x, series.to_numpy())
    residual = series.to_numpy() - model.predict(x)
    sigma = float(np.std(residual))
    points = []
    for day in range(1, 31):
        predicted = model.predict(np.arange(len(series), len(series) + day).reshape(-1, 1)).sum()
        estimate = balance + float(predicted)
        margin = 1.282 * sigma * np.sqrt(day)
        points.append({"date": str(today + timedelta(days=day)), "balance": round(estimate, 2), "lower": round(estimate - margin, 2), "upper": round(estimate + margin, 2)})
    return {"status": "ready", "points": points, "history_days": len(series), "method": "Linear regression on daily net cash flow including zero-activity days; cumulative residual interval.", "limitations": limitations}
