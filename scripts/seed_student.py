"""Append explicitly fictional final-year student finances to an existing local account.

Example: python scripts/seed_student.py --user-id 2 --as-of 2026-11-14
Uses the local SQLite demo database, preserves existing records, and is repeat-safe.
"""
import argparse
import calendar
from datetime import date, timedelta
from pathlib import Path
import random
import sqlite3

MARKER = "Fictional final-year student scenario v1; academic demonstration only."
ROOT = Path(__file__).resolve().parents[1]


def seed(user_id, today, database):
    rng = random.Random(20261114)
    with sqlite3.connect(database, timeout=30) as db:
        db.execute("PRAGMA foreign_keys=ON")
        user = db.execute("SELECT name FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            raise ValueError("Target account does not exist")
        if db.execute("SELECT 1 FROM transactions WHERE user_id=? AND notes=? LIMIT 1", (user_id, MARKER)).fetchone():
            print("Student scenario already present; no records added.")
            return

        backup_dir = ROOT / ".tools" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"before-student-seed-user-{user_id}-{today}.db"
        if backup.exists():
            print("Student seed backup already exists; skipping to avoid duplicate records.")
            return
        with sqlite3.connect(backup) as destination:
            db.backup(destination)

        records = []
        def add(day, title, amount, kind, category):
            if day <= today:
                records.append((user_id, title.removesuffix(" - fictional"), amount, kind, category, day.isoformat(), ""))

        index = today.year * 12 + today.month - 1
        for offset in range(5, -1, -1):
            year, month_zero = divmod(index-offset, 12)
            month = month_zero+1
            first = date(year, month, 1)
            last = min(date(year, month, calendar.monthrange(year, month)[1]), today)
            add(first, "Family allowance - fictional", 10000, "income", "Other")
            add(date(year, month, 5), "Part-time web internship stipend - fictional", 6500, "income", "Salary")
            add(date(year, month, 2), "Shared student accommodation - fictional", 4500, "expense", "Housing")
            add(date(year, month, 4), "Student mobile recharge - fictional", 299, "expense", "Utilities")
            add(date(year, month, 6), "Shared Wi-Fi contribution - fictional", 250, "expense", "Utilities")
            add(date(year, month, 8), "Cloud storage plan - fictional", 130, "expense", "Utilities")
            add(date(year, month, 9), "Music student plan - fictional", 59, "expense", "Entertainment")
            add(date(year, month, 10), "Project printing and binding - fictional", rng.randint(180, 420), "expense", "Education")
            add(date(year, month, 12), "Programming course - fictional", 499, "expense", "Education")
            add(date(year, month, 18), "Freelance website assignment - fictional", 2200, "income", "Freelance")
            add(date(year, month, 20), "Student movie outing - fictional", 240, "expense", "Entertainment")
            add(date(year, month, 23), "Stationery and notebooks - fictional", rng.randint(100, 260), "expense", "Education")
            day = first
            while day <= last:
                if day.weekday() < 5:
                    add(day, "College canteen lunch - fictional", rng.choice([60, 70, 80, 90, 110]), "expense", "Food & Dining")
                    add(day, "Bus and metro commute - fictional", rng.choice([40, 50, 60]), "expense", "Transport")
                    if day.weekday() in (1, 3):
                        add(day, "Tea and evening snack - fictional", rng.choice([25, 35, 45]), "expense", "Food & Dining")
                elif day.weekday() == 5:
                    add(day, "Weekly groceries - fictional", rng.randint(200, 380), "expense", "Food & Dining")
                day += timedelta(days=1)

        add(today-timedelta(days=6), "Final-year project components - fictional", 2200, "expense", "Education")
        add(today-timedelta(days=3), "External SSD for project backup - fictional", 3800, "expense", "Shopping")
        add(today-timedelta(days=1), "Placement interview travel - fictional", 180, "expense", "Transport")

        # One transaction: either all scenario rows are committed, or none are.
        db.execute("BEGIN IMMEDIATE")
        db.executemany("INSERT INTO transactions (user_id,title,amount,kind,category,date,notes) VALUES (?,?,?,?,?,?,?)", records)
        budgets = 0
        for offset in range(5, -1, -1):
            year, month_zero = divmod(index-offset, 12)
            key = f"{year:04d}-{month_zero+1:02d}"
            for category, amount in [("All",14000),("Housing",4500),("Food & Dining",4000),("Transport",1500),("Education",1500),("Shopping",2500),("Entertainment",600),("Utilities",1000)]:
                if not db.execute("SELECT 1 FROM budgets WHERE user_id=? AND month=? AND category=?", (user_id,key,category)).fetchone():
                    db.execute("INSERT INTO budgets (user_id,month,category,amount) VALUES (?,?,?,?)", (user_id,key,category,amount))
                    budgets += 1
        subscriptions = 0
        for name, amount, days, category in [("Music student plan - fictional",59,5,"Entertainment"),("Cloud storage plan - fictional",130,8,"Utilities"),("Student mobile recharge - fictional",299,12,"Utilities")]:
            name = name.removesuffix(" - fictional")
            if not db.execute("SELECT 1 FROM subscriptions WHERE user_id=? AND name=?",(user_id,name)).fetchone():
                db.execute("INSERT INTO subscriptions (user_id,name,amount,cycle,next_due,category,active) VALUES (?,?,?,?,?,?,?)", (user_id,name,amount,"monthly",(today+timedelta(days=days)).isoformat(),category,1))
                subscriptions += 1
        db.commit()
        print(f"Added fictional student scenario for {user[0]}: {len(records)} transactions, {budgets} budgets, {subscriptions} subscriptions.")
        print(f"Existing data backup: {backup}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    database = ROOT / "backend" / "verification.db"
    if not database.exists():
        raise SystemExit("Local verification database not found")
    seed(args.user_id, args.as_of, database)
