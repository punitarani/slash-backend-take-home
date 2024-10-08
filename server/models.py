"""models.py"""

from enum import Enum

from sqlalchemy import DECIMAL, TIMESTAMP, Column, ForeignKey, String, func
from sqlalchemy.orm import relationship

from db import Base


class TransactionType(str, Enum):
    deposit = "deposit"
    withdraw_request = "withdraw_request"
    withdraw = "withdraw"


class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True)
    balance = Column(DECIMAL(10, 2), nullable=False, default=0)

    transactions = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    accountId = Column(
        String, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(String, nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    account = relationship("Account", back_populates="transactions")
