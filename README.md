# Slash backend take home

![Architecture](Slash%20Backend.png)

### Database

We are using a postgres database with the following tables.

> We also have a plpgsql function to create account, if it doesn't exist while adding a transaction.
> This will not be there in production as the account will exist beforehand.

```sql
CREATE TABLE accounts
(
    id      TEXT PRIMARY KEY,
    balance DECIMAL(10, 2) NOT NULL
);

CREATE TABLE transactions
(
    id        TEXT PRIMARY KEY,
    accountId TEXT REFERENCES accounts (id) ON DELETE CASCADE,
    type      TEXT           NOT NULL,
    amount    DECIMAL(10, 2) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API (Client Facing)

The API is built using FastAPI. It has the following endpoints.

The OpenAPI schema is in `openapi.json`.

- `POST /transaction`
    - This is the main endpoint that processes transactions from the client.
    - It adds the transaction to the message queue (RabbitMQ in this case).
    - The worker will process the transaction and update the database.
    - If the transaction is a `withdraw_request`, it will respond with the appropriate status immediately by checking
      the SQL database.
    - If the transaction is a `deposit` or a `withdraw`, it responds with an appriate status but the actual processing
      of these transactions is done in the worker.
- `GET /account/{accountId}`
    - This simply returns the account balance for the given account id from the database.
    - If a transaction is processing (i.e. still in the queue), it will

#### Debug

- Added /debug endpoints to get a db dump
    - `/debug/accocunts` returns the entire `accounts` table
    - `/debug/transactions` returns the entire `transactions` table

### Worker (Transactions Processor)

The worker is a RabbitMQ consumer designed for processing transactions asynchronously:

- Connects to RabbitMQ with fault-tolerant parameters (heartbeat and timeout).
- Processes each transaction within a database session:
    - Checks for duplicate transactions to prevent double-processing.
    - Creates accounts if they don't exist.
- Implements error handling:
    - Database errors trigger a rollback and message requeue.
    - General exceptions are logged and messages are requeued.

This design ensures robustness, data consistency, and scalability in processing transactions.

### Features

- **Fault Tolerance and Data Integrity**
    - RabbitMQ ensures transactions are not lost if servers or database go down
    - Multiple API server replicas behind nginx for continued operation if some servers fail
    - Database transactions are rolled back if any error occurs in the worker
    - Server restart policy is set to always that the API and worker can automatically restart without manual
      intervention (good for now)

- **Transaction Accuracy**
    - Postgres database maintains accurate ledger of all transactions after processing
    - Withdrawal requests prevented if they would result in negative balance
    - Asynchronous processing via worker ensures consistent account updates

- **Performance Optimization**
    - Asynchronous transaction processing with RabbitMQ for high throughput
    - Database connection pooling for efficient database access
    - Horizontally scalable architecture to handle increased load

### Future Work

This is an MVP to test the core functionality and a proof-of-concept. Not everything is perfect, optimized, or
production-ready.

- Use Asyncio for Postgres and RabbitMQ to be more performant. Currently, we are using `psycopg2` and `pika` which are
  not async. This can be updated to use `asyncpg` and `aiopika` for asyncio and significantly improve the performance
  while waiting for database transactions to process.
- Handle 'pending' transactions in the queue as deposits/withdrawls can take time to process.
- Handle 'withdraw_request` better by placing a hold on the amount requested.
    - In real-world, deposits can take time to process, so we need to hold the requested amount.
- Add auth
- Add db backup
- Add logging, monitoring, and observability
- Split the deployments so that the Database for example can be in a different deployment than the API and worker. This
  will allow us to scale them independently.
