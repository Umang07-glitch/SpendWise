"""Explicit, idempotent fictional data seed: python -m app.seed."""
from datetime import date, timedelta
from decimal import Decimal
import random
from sqlalchemy import select
from .database import SessionLocal
from .models import User, Transaction, Budget, Subscription
from .security import hash_password


def seed():
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "demo@example.com")):
            print("Fictional demo account already exists; seed skipped.")
            return
        user = User(email="demo@example.com", name="Aarav Sharma", password_hash=hash_password("DemoSpendWise!2026"))
        db.add(user)
        db.flush()
        today = date.today()
        rng = random.Random(42)
        merchants = [("Green Basket groceries", "Food & Dining", 450, 1800), ("Metro commute", "Transport", 80, 300), ("Corner Cafe", "Food & Dining", 150, 700), ("Bookshop", "Shopping", 300, 2000), ("Weekend cinema", "Entertainment", 400, 1200), ("Electricity bill", "Utilities", 900, 2300)]
        for day in range(180):
            d = today-timedelta(days=day)
            if d.day == 1:
                db.add(Transaction(user_id=user.id, title="Fictional Studio salary", amount=Decimal("85000"), kind="income", category="Salary", date=d, notes="Fictional seed data"))
                db.add(Transaction(user_id=user.id, title="Apartment rent", amount=Decimal("18000"), kind="expense", category="Housing", date=d, notes="Fictional seed data"))
            if day % 13 == 0:
                db.add(Transaction(user_id=user.id, title="Freelance design project", amount=Decimal("6500"), kind="income", category="Freelance", date=d, notes="Fictional seed data"))
            if rng.random() < .8:
                title, category, low, high = rng.choice(merchants)
                db.add(Transaction(user_id=user.id, title=title, amount=Decimal(rng.randint(low,high)), kind="expense", category=category, date=d, notes="Fictional seed data"))
        db.add(Transaction(user_id=user.id, title="Fictional laptop purchase", amount=Decimal("64000"), kind="expense", category="Shopping", date=today-timedelta(days=3), notes="Fictional one-off purchase"))
        for cat, amount in [("All",55000),("Food & Dining",8000),("Shopping",10000),("Transport",4000),("Housing",18000),("Entertainment",3000)]:
            db.add(Budget(user_id=user.id, month=today.strftime("%Y-%m"), category=cat, amount=Decimal(amount)))
        for name, amount, days, cycle in [("Spotify",119,3,"monthly"),("Netflix",499,7,"monthly"),("Cloud storage",1300,16,"yearly")]:
            db.add(Subscription(user_id=user.id, name=name, amount=Decimal(amount), cycle=cycle, next_due=today+timedelta(days=days), category="Entertainment", active=True))
        db.commit()
        print("Created fictional demo account: demo@example.com / DemoSpendWise!2026")


if __name__ == "__main__":
    seed()
