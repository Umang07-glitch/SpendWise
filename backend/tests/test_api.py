from datetime import date, timedelta
import io
import csv
from app.security import hash_password, verify_password


def tx(**updates):
    return {"title":"Grocery", "amount":"450.50", "kind":"expense", "category":"Food & Dining", "date":str(date.today()), "notes":"", **updates}


def test_passwords_are_salted():
    a, b = hash_password("password"), hash_password("password")
    assert a != b and verify_password("password",a) and not verify_password("wrong",a)


def test_auth_throttling_and_origin(client):
    payload={"email":"missing@example.com","password":"wrong"}
    assert client.post("/auth/login",json=payload,headers={"Origin":"https://untrusted.example"}).status_code == 403
    for _ in range(20):
        assert client.post("/auth/login",json=payload).status_code == 401
    result=client.post("/auth/login",json=payload)
    assert result.status_code == 429 and result.headers["Retry-After"] == "60"


def test_auth_lifecycle(client):
    assert client.get("/auth/me").status_code == 401
    r = client.post("/auth/register",json={"name":"User","email":"user@example.com","password":"password-long"})
    assert r.status_code == 201
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=lax" in r.headers["set-cookie"]
    csrf = r.json()["csrf"]
    assert "password_hash" not in r.json()["user"]
    assert client.post("/auth/logout").status_code == 403
    assert client.post("/auth/logout",headers={"X-CSRF-Token":csrf}).status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login",json={"email":"user@example.com","password":"wrong"}).status_code == 401
    assert client.post("/auth/login",json={"email":"user@example.com","password":"password-long"}).status_code == 200
    assert client.post("/auth/register",json={"name":"User","email":"USER@example.com","password":"password-long"}).status_code == 409


def test_transactions_crud_filters_and_validation(client, auth):
    assert client.post("/transactions",json=tx()).status_code == 403
    for changes in [{"amount":"-1"},{"amount":"1.001"},{"kind":"transfer"},{"category":"Unknown"},{"date":"bad"}]:
        assert client.post("/transactions",json=tx(**changes),headers=auth).status_code == 422
    r=client.post("/transactions",json=tx(),headers=auth)
    assert r.status_code == 201
    record=r.json()["id"]
    assert client.get("/transactions?search=Groc&category=Food%20%26%20Dining&kind=expense").json()["total"] == 1
    assert client.get("/transactions?kind=income").json()["total"] == 0
    assert client.get("/transactions?page=0").status_code == 422
    assert client.put(f"/transactions/{record}",json=tx(amount="900"),headers=auth).json()["amount"] == "900"
    assert client.delete(f"/transactions/{record}",headers=auth).status_code == 204
    assert client.get("/transactions").json()["total"] == 0


def test_cross_user_isolation(client,auth):
    t=client.post("/transactions",json=tx(),headers=auth).json()["id"]
    b=client.post("/budgets",json={"month":date.today().strftime("%Y-%m"),"category":"All","amount":"1000"},headers=auth).json()["id"]
    s=client.post("/subscriptions",json={"name":"Music","amount":"99","cycle":"monthly","next_due":str(date.today()),"category":"Entertainment"},headers=auth).json()["id"]
    other=client.post("/auth/register",json={"name":"Other","email":"other@example.com","password":"another-password"}).json()
    headers={"X-CSRF-Token":other["csrf"]}
    assert client.get("/transactions").json()["total"] == 0
    assert client.get("/subscriptions").json()["items"] == []
    for path in [f"/transactions/{t}",f"/budgets/{b}",f"/subscriptions/{s}"]:
        assert client.delete(path,headers=headers).status_code == 404
    assert client.put(f"/transactions/{t}",json=tx(),headers=headers).status_code == 404
    assert client.get("/export/transactions").text.count("Grocery") == 0
    assert client.get("/forecast").json()["status"] == "insufficient_data"


def test_dashboard_reports_budgets(client,auth):
    month=date.today().strftime("%Y-%m")
    client.post("/transactions",json=tx(amount="1000",kind="income",category="Salary"),headers=auth)
    client.post("/transactions",json=tx(amount="450"),headers=auth)
    d=client.get(f"/dashboard?month={month}").json()
    assert float(d["income"]) == 1000 and float(d["expenses"]) == 450
    assert float(d["savings"]) == 550 and float(d["balance"]) == 550 and d["savings_rate"] == 55
    assert len(d["trends"]) == 6
    budget={"month":month,"category":"All","amount":"300"}
    r=client.post("/budgets",json=budget,headers=auth)
    assert r.status_code == 201
    record=r.json()["id"]
    assert client.post("/budgets",json=budget,headers=auth).status_code == 409
    data=client.get(f"/budgets?month={month}").json()[0]
    assert data["overspent"] and float(data["remaining"]) == -150
    assert client.put(f"/budgets/{record}",json={**budget,"amount":"600"},headers=auth).status_code == 200
    assert not client.get(f"/budgets?month={month}").json()[0]["overspent"]
    assert client.get(f"/reports?month={month}").json() == d
    assert "Food & Dining" in client.get(f"/export/report?month={month}").text
    assert client.get("/dashboard?month=2026-13").status_code == 422
    assert client.delete(f"/budgets/{record}",headers=auth).status_code == 204


def test_atomic_csv_and_formula_protection(client,auth):
    content="title,amount,kind,category,date,notes\nCafe,120,expense,Food & Dining,2026-01-01,ok\nBad,-1,expense,Other,2026-01-01,invalid\n"
    assert client.post("/import/transactions",files={"file":("test.csv",content)},headers=auth).status_code == 422
    assert client.get("/transactions").json()["total"] == 0
    valid=content.split("Bad")[0]
    assert client.post("/import/transactions",files={"file":("test.csv",valid)},headers=auth).json()["imported"] == 1
    client.post("/transactions",json=tx(title="=CMD()"),headers=auth)
    rows=list(csv.reader(io.StringIO(client.get("/export/transactions").text)))
    assert any(row[0]=="'=CMD()" for row in rows)
    assert client.post("/import/transactions",files={"file":("test.csv","x\n1")},headers=auth).status_code == 422


def test_subscriptions_profile_and_insights(client,auth):
    sub={"name":"Storage","amount":"1200","cycle":"yearly","next_due":str(date.today()),"category":"Utilities"}
    record=client.post("/subscriptions",json=sub,headers=auth).json()["id"]
    assert float(client.get("/subscriptions").json()["monthly_cost"]) == 100
    assert client.put(f"/subscriptions/{record}",json={**sub,"active":False},headers=auth).status_code == 200
    assert float(client.get("/subscriptions").json()["monthly_cost"]) == 0
    assert client.patch("/profile",json={"name":"Updated","currency":"USD","notifications":False},headers=auth).json()["currency"] == "USD"
    assert client.patch("/profile",json={"name":"Updated","currency":"XXX"},headers=auth).status_code == 422
    assert client.get("/categorize?title=Uber%20trip").json()["category"] == "Transport"
    assert client.get("/categorize?title=Something").json()["category"] == "Other"
    assert client.get("/insights").json()["unusual"] == []
    for i in range(20):
        client.post("/transactions",json=tx(amount=str(100+i*10),date=str(date.today()-timedelta(days=i))),headers=auth)
    client.post("/transactions",json=tx(amount="99999"),headers=auth)
    assert len(client.get("/insights").json()["unusual"]) > 0
    forecast=client.get("/forecast").json()
    assert forecast["status"] == "ready" and len(forecast["points"]) == 30
    assert forecast["limitations"] and all(p["lower"]<=p["balance"]<=p["upper"] for p in forecast["points"])
    assert client.delete(f"/subscriptions/{record}",headers=auth).status_code == 204
