"""schemas.py"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AccountBalance(BaseModel):
    id: str
    balance: Decimal

    class Config:
        from_attributes = True


class Transaction(BaseModel):
    id: str
    type: str
    amount: float
    account_id: str = Field(..., alias="accountId")
    timestamp: datetime

    class Config:
        from_attributes = True
