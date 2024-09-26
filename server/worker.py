"""worker.py

RabbitMQ worker process for handling transactions.
"""

import json
import os
from datetime import datetime
from decimal import Decimal

import pika
from sqlalchemy.exc import SQLAlchemyError

import models
from db import SessionLocal

# RabbitMQ configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_QUEUE = "transactions_queue"

# Establish connection to RabbitMQ
parameters = pika.ConnectionParameters(
    host=RABBITMQ_HOST, heartbeat=600, blocked_connection_timeout=300
)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)


def process_transaction(ch, method, properties, body):
    """
    Process a transaction received from the RabbitMQ queue.
    """
    with SessionLocal() as db:
        try:
            message = json.loads(body)
            transaction_id = message["id"]
            print(f"Processing transaction: {transaction_id}")
            transaction_type = message["type"]
            accountId = message["accountId"]
            amount = Decimal(message["amount"])
            timestamp = datetime.fromisoformat(message["timestamp"])

            # Check if transaction already exists
            existing_transaction = (
                db.query(models.Transaction)
                .filter(models.Transaction.id == transaction_id)
                .first()
            )
            if existing_transaction:
                # Transaction already processed, acknowledge and skip
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Fetch account and perform transaction
            account = (
                db.query(models.Account)
                .filter(models.Account.id == accountId)
                .with_for_update()
                .first()
            )
            if not account:
                # Account does not exist, create it
                account = models.Account(id=accountId, balance=0)
                db.add(account)
                db.flush()

            # Handle deposit and withdraw
            if transaction_type == "deposit":
                account.balance += amount
            elif transaction_type == "withdraw_request":
                # Record the withdraw_request transaction without changing the balance
                pass
            elif transaction_type == "withdraw":
                account.balance -= amount
                # Allow balance to go negative as per specification

            # Save transaction record
            new_transaction = models.Transaction(
                id=transaction_id,
                accountId=accountId,
                type=transaction_type,
                amount=amount,
                timestamp=timestamp,
            )
            db.add(new_transaction)
            db.commit()

            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except SQLAlchemyError as e:
            db.rollback()
            # Log error and requeue message if a database error occurs
            print(f"Database error processing transaction: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        except Exception as e:
            # Log general error
            print(f"Error processing transaction: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def consume_transactions():
    """
    Start consuming transactions from the RabbitMQ queue.
    """
    print("Worker started, waiting for messages...")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=process_transaction)
    channel.start_consuming()


if __name__ == "__main__":
    consume_transactions()
