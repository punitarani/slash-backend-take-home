"""api.py

Client API for the transaction processing service.
"""

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import pika
from fastapi import Body, Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

import models
import schemas
from db import Base, engine, get_db

# RabbitMQ configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = "transactions_queue"

# Establish connection to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()
channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    Base.metadata.create_all(bind=engine)

    # Initialize RabbitMQ connection and channel
    global rabbitmq_connection
    global rabbitmq_channel

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST, heartbeat=600, blocked_connection_timeout=300
    )
    rabbitmq_connection = pika.BlockingConnection(parameters)
    rabbitmq_channel = rabbitmq_connection.channel()
    rabbitmq_channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    yield

    # Close RabbitMQ connection
    rabbitmq_connection.close()


app = FastAPI(lifespan=lifespan)


@app.post("/transaction")
async def create_transaction(
    transaction: schemas.Transaction = Body(
        ..., alias="transaction", allow_population_by_field_name=True
    ),
    db: Session = Depends(get_db),
):
    """
    Process a transaction

    Args:
        transaction (schemas.Transaction): The transaction details.
        db (Session): The database session.

    Returns:
        dict: A message indicating the transaction status.

    Raises:
        HTTPException: If the account is not found or there are issues with the withdrawal.
    """
    # Verify if the transaction has already been processed
    existing_transaction = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction.id)
        .first()
    )
    if existing_transaction:
        return {"detail": "Transaction already processed"}, 200

    # Verify account existence
    account = (
        db.query(models.Account)
        .filter(models.Account.id == transaction.account_id)
        .first()
    )
    if not account:
        # If account doesn't exist, create it with zero balance
        account = models.Account(id=transaction.account_id, balance=0)
        db.add(account)
        db.commit()
        db.refresh(account)

    if transaction.type == "withdraw_request":
        start_time = time.time()

        # Check if balance is sufficient
        if account.balance >= transaction.amount:
            # Approve the request
            # Enqueue the withdraw_request transaction
            message = transaction.model_dump()
            message["timestamp"] = message[
                "timestamp"
            ].isoformat()  # Convert datetime to string
            rabbitmq_channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            # Enqueue the subsequent withdraw transaction
            withdraw_transaction = schemas.Transaction(
                id=str(uuid.uuid4()),
                type="withdraw",
                amount=transaction.amount,
                account_id=transaction.account_id,
                timestamp=datetime.utcnow(),
            )
            message = withdraw_transaction.model_dump()
            message["timestamp"] = message[
                "timestamp"
            ].isoformat()  # Convert datetime to string
            rabbitmq_channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            elapsed_time = time.time() - start_time
            if elapsed_time > 3:
                raise HTTPException(
                    status_code=402, detail="Withdraw_request timed out"
                )
            return {"detail": "withdraw_request approved"}, 201
        else:
            # Reject the request
            raise HTTPException(status_code=402, detail="Insufficient funds")

    else:
        # For other transactions, check for valid type and enqueue them
        if transaction.type not in ["deposit", "withdraw"]:
            raise HTTPException(status_code=400, detail="Invalid transaction type")
        message = transaction.model_dump()
        message["timestamp"] = message[
            "timestamp"
        ].isoformat()  # Convert datetime to string
        rabbitmq_channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        return {"detail": "Transaction received"}, 200


@app.get("/account/{account_id}", response_model=schemas.AccountBalance)
async def get_account_balance(account_id: str, db: Session = Depends(get_db)):
    """
    Get account balance

    Args:
        account_id (str): The ID of the account.
        db (Session): The database session.

    Returns:
        schemas.AccountBalance: The account ID and current balance.

    Raises:
        HTTPException: If the account is not found.
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return schemas.AccountBalance(id=account.id, balance=account.balance)


@app.get("/debug/accounts", response_model=list[schemas.AccountBalance])
async def list_accounts(db: Session = Depends(get_db)):
    """
    USED FOR DEBUGGING AND TESTING.
    Retrieve a list of all accounts and their balances.

    Args:
        db (Session): The database session.

    Returns:
        list[schemas.Account]: A list of accounts with their IDs and balances.
    """
    accounts = db.query(models.Account).all()
    return [
        schemas.AccountBalance(id=account.id, balance=account.balance)
        for account in accounts
    ]


@app.get("/debug/transactions", response_model=list[schemas.Transaction])
async def list_transactions(db: Session = Depends(get_db)):
    """
    USED FOR DEBUGGING AND TESTING.
    Retrieve a list of all transactions.

    Args:
        db (Session): The database session.

    Returns:
        list[schemas.Transaction]: A list of all transactions.
    """
    transactions = db.query(models.Transaction).all()
    return [
        schemas.Transaction(
            id=transaction.id,
            type=transaction.type,
            amount=float(transaction.amount),
            account_id=transaction.account_id,
            timestamp=transaction.timestamp,
        )
        for transaction in transactions
    ]


@app.get("/status")
async def get_status(db: Session = Depends(get_db)):
    """
    Check the status of the API, worker, PostgreSQL, and RabbitMQ.

    Returns:
        dict: Status of each component.
    """

    status = {"api": "healthy", "db": "healthy", "rabbitmq": "healthy"}

    # Check Postgres
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        status["db"] = f"unhealthy: {str(e)}"

    # Check RabbitMQ
    try:
        _connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        _connection.close()
    except Exception as e:
        status["rabbitmq"] = f"unhealthy: {str(e)}"

    return status
