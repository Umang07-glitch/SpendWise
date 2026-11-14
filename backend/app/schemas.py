from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

CATEGORIES = ["Salary", "Freelance", "Food & Dining", "Shopping", "Transport", "Housing", "Utilities", "Entertainment", "Health", "Education", "Travel", "Other"]
Money = Field(gt=0, le=999999999999, max_digits=14, decimal_places=2)


class Register(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Profile(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    currency: Literal["INR", "USD", "EUR", "GBP"] = "INR"
    notifications: bool = True


class TransactionIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    amount: Decimal = Money
    kind: Literal["income", "expense"]
    category: str = "Other"
    date: date
    notes: str = Field(default="", max_length=500)

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError("Unknown category")
        return v


class TransactionOut(TransactionIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class BudgetIn(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    category: str
    amount: Decimal = Money

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in [*CATEGORIES, "All"]:
            raise ValueError("Unknown category")
        return v


class SubscriptionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Money
    cycle: Literal["monthly", "yearly"]
    next_due: date
    category: str = "Entertainment"
    active: bool = True

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError("Unknown category")
        return v
