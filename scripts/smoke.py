"""HTTP smoke test against a seeded running frontend and its FastAPI proxy.

Usage: python scripts/smoke.py [http://localhost:3000]
Only use this against a local fictional development database.
"""
import sys
from datetime import date
import httpx

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
month = date.today().strftime("%Y-%m")
with httpx.Client(base_url=base, timeout=60) as client:
    for path in ("/", "/transactions", "/budgets", "/subscriptions", "/insights", "/forecast", "/reports", "/settings"):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        assert "SpendWise" in response.text
    assert client.get("/api/auth/me").status_code == 401
    login = client.post("/api/auth/login", json={"email":"demo@example.com", "password":"DemoSpendWise!2026"})
    assert login.status_code == 200, login.text
    headers={"X-CSRF-Token":login.json()["csrf"]}
    for path in ("/auth/me", "/categories", f"/dashboard?month={month}", "/transactions?page=1", f"/budgets?month={month}", "/subscriptions", "/insights", "/forecast", f"/reports?month={month}", "/export/transactions", f"/export/report?month={month}"):
        result=client.get("/api"+path)
        assert result.status_code == 200, (path,result.text)
    row={"title":"Fictional HTTP smoke check", "amount":"1.25", "kind":"expense", "category":"Other", "date":str(date.today()), "notes":"Disposable automated smoke-test record"}
    result=client.post("/api/transactions", json=row, headers=headers)
    assert result.status_code == 201, result.text
    record_id=result.json()["id"]
    try:
        result=client.put(f"/api/transactions/{record_id}", json={**row,"amount":"2.50"}, headers=headers)
        assert result.status_code == 200 and float(result.json()["amount"]) == 2.5
    finally:
        assert client.delete(f"/api/transactions/{record_id}",headers=headers).status_code == 204
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
print("PASS: 8 frontend routes, 11 authenticated proxy reads, transaction create/update/delete, login/logout and protected access.")
