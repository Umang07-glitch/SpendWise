from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(300))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    notifications: Mapped[bool] = mapped_column(default=True)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (CheckConstraint("amount > 0"), CheckConstraint("kind IN ('income', 'expense')"), Index("ix_tx_user_date", "user_id", "date"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    kind: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(40))
    date: Mapped[date]
    notes: Mapped[str] = mapped_column(String(500), default="")


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "month", "category"), CheckConstraint("amount > 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    month: Mapped[str] = mapped_column(String(7))
    category: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (CheckConstraint("amount > 0"), CheckConstraint("cycle IN ('monthly', 'yearly')"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cycle: Mapped[str] = mapped_column(String(10))
    next_due: Mapped[date]
    category: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(default=True)
