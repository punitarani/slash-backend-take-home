# Slash backend take home

## Punit's Notes

- Add redis db to store the transactions and account balances
  - Is it the best? No, but for the scope of this exercise, it should be fine.
  - In a prod env, we would use a sql db to store the transactions and account balances
  - Redis however should allow horizontal scaling as multiple replicas can access the same data
- Add a `/status` endpoint to the API to check the health of the service
  - This is primarily used for debugging and ensuring redis connection is alive
- Added helper db functions to handle queries to the redis db
- Updated existing endpoints to use the new db functions

---

We're looking for strong backend engineers who are capable of building performant and fault-tolerant systems that scale. We want engineers who can think and ship quickly, and are focused on getting things done. If you are looking for more product-focused or frontend roles, check out our other challenges:

- [Slash frontend take home](https://github.com/kevinbai0/slash-frontend-take-home)
- [Slash full stack take home](https://github.com/kevinbai0/slash-fullstack-take-home)

Clone this repository and push it to a private repo you own. Once you're done, shoot us an email to [engineering@joinslash.com](mailto:engineering@joinslash.com) and share your private Github repository with [@kevinbai0](https://github.com/kevinbai0).

### Overview

Slash keeps track of all balances in real-time for customers by maintaining a ledger of all transactions. For this challenge, you will implement a service that receives incoming transactions, and responds (approve or reject) to transaction requests based off the account's current balance. 

### Requirements

1. Write a web server that conforms to the [specification](#specification). Your web server should be horizontally scalable. It will be ran with several replicas behind an nginx proxy. Your web-server should read the `PORT` environment variable to know which port to listen on.
2. You can use any services that you see fit (like a database). While we want you to build this out with production in mind, the take home is still a proof-of-concept so there is no need to consider auth, or any complex deployment configurations.
3. The system should be robust and fault-tolerant. If any resources go down, data should not be lost.
4. Correctness is important. The ledger should maintain an accurate record of all transactions, and accounts should not be able to reach a negative balance.
5. Make your system as performant as possible. We will stress test your service.

### Instructions

1. Clone this repository (and push to a private one).
2. Run `npm install` to install dependencies.
3. Edit the Dockerfile to build and run your web server (you can work off the existing one too). You can use any language or framework as you see fit.
4. Make sure your application listens on the port specified in the nginx.conf file.
5. Run `docker compose up` to start the nginx proxy and your server.
6. To test, `npm run test test-0` runs the `src/tests/test-0.ts` test.
7. Copy the command outputted by the test and paste it (`npm run check <path>`) to check the result of the test.

See [examples](#examples) on expected behavior for edge cases.

By default, `src/server.ts` is a simple in-memory implementation of a sample single-node server. You may choose to build on top off of this template, or start from scratch.

You may also choose to make whatever changes you'd like to the docker-compose.yaml file. You must still make sure that a web server is exposed through port 80 (which is what nginx exposes).


### Time constraints

Spend as much time as you'd like on the challenge, but don't spend more than 8 hours unless you're _really_ enjoying it and want to go the extra mile. Try spending at least 2 hours, and if you don't have time after that, let us know so we can evaluate accordingly (no penalty for the amount of time you spent, just be honest!).

### Specification

Your web server should conform to the following OpenAPI specification:

```yaml
openapi: 3.0.0
info:
  title: Transaction API
  version: 1.0.0
  description: API for handling transactions and account balances

paths:
  /transaction:
    post:
      summary: Process a transaction
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Transaction'
      responses:
        '200':
          description: Transaction processed successfully
        '201':
          description: Withdrawal request approved
        '402':
          description: Withdrawal request denied

  /account/{accountId}:
    get:
      summary: Get account balance
      parameters:
        - name: accountId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AccountBalance'

components:
  schemas:
    Transaction:
      type: object
      properties:
        id:
          type: string
        type:
          type: string
          enum: [deposit, withdraw_request, withdraw]
        amount:
          type: number
        accountId:
          type: string
        timestamp:
          type: string # ISO timestamp
      required:
        - id
        - type
        - amount
        - accountId
        - timestamp

    AccountBalance:
      type: object
      properties:
        accountId:
          type: string
        balance:
          type: number
      required:
        - accountId
        - balance
```

Withdraw requests should respond within 3 seconds. Otherwise, we assume a timeout and reject the request.

### Examples

Requests may look like the following:
```sh
curl -X POST http://localhost:80/transaction -H "Content-Type: application/json" -d '{"id": "1", "type": "deposit", "amount": 100, "accountId": "123", "timestamp": "2023-01-01T00:00:00Z"}'

curl http://localhost:80/account/123
# should return a balance of 100

curl -X POST http://localhost:80/transaction -H "Content-Type: application/json" -d '{"id": "2", "type": "withdraw_request", "amount": 50, "accountId": "123", "timestamp": "2023-01-01T00:00:01Z"}' 
# should respond with a 201

curl -X POST http://localhost:80/transaction -H "Content-Type: application/json" -d '{"id": "3", "type": "withdraw_request", "amount": 51, "accountId": "123", "timestamp": "2023-01-01T00:00:02Z"}'
# should respond with a 402 because if we approve both, the balance will go negative

curl http://localhost:80/account/123
# should return a balance of 100 still because we haven't received any actual "withdraw"s yet

curl -X POST http://localhost:80/transaction -H "Content-Type: application/json" -d '{"id": "4", "type": "withdraw", "amount": 50, "accountId": "123", "timestamp": "2023-01-01T00:00:03Z"}'
# should respond with a 200

curl http://localhost:80/account/123
# should return a balance of 50

curl -X POST http://localhost:80/transaction -H "Content-Type: application/json" -d '{"id": "5", "type": "withdraw", "amount": 50, "accountId": "123", "timestamp": "2023-01-01T00:00:04Z"}'
# should respond with 200. There doesn't necessarily need to be a withdraw_request before a withdraw.
# assuming your implementation is correct, a withdraw without a withdraw_request will never be more
# than the current balance.

curl -X POST http://localhost:80/transaction -H "Content-Type: application/json" -d '{"id": "6", "type": "withdraw", "amount": 100, "accountId": "123", "timestamp": "2023-01-01T00:00:05Z"}'
# last withdraw request should technically never happen, but if it does, 
# something went wrong. We can't block the transaction from happening, so we must allow it.

curl http://localhost:80/account/123
# should return a balance of -100 (because of the last withdraw that shouldn't have happened)
```

## Notes

Please write and commit any notes while you're working on the challenge or after you're done. For example, are there things you would do in production, but don't have time to do now? What tradeoffs did you make with respect to time constraints? If you had 1 week to build this, what else would you consider? 
