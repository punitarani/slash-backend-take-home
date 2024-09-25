import express from "express";
import { Redis } from "ioredis";

const app = express();
app.use(express.json());

interface Transaction {
	id: string;
	type: "deposit" | "withdraw_request" | "withdraw";
	amount: number;
	accountId: string;
	timestamp: string;
}

// interface AccountBalance {
// 	accountId: string;
// 	balance: number;
// }

// const transactions: {
// 	[Key in string]: Transaction[];
// } = {};

// Create a Redis client
const redis = new Redis(process.env.REDIS_URL || "redis://localhost:6379");

// Get the balance for an account from Redis
async function getBalance(accountId: string): Promise<number> {
	// balance:accountId -> $balance
	const balance = await redis.get(`balance:${accountId}`);
	return balance ? Number.parseFloat(balance) : 0;
}

// Set the balance for an account in Redis
async function setBalance(accountId: string, amount: number): Promise<void> {
	// balance:accountId -> $balance
	await redis.set(`balance:${accountId}`, amount.toString());
}

// Add a new transaction for an account in Redis
async function addTransaction(
	accountId: string,
	transaction: Transaction,
): Promise<void> {
	// transactions:accountId:transactionId -> $transaction
	await redis.set(
		`transactions:${accountId}:${transaction.id}`,
		JSON.stringify(transaction),
	);
}

// Get the transactions for an account from Redis
async function getTransactions(accountId: string): Promise<Transaction[]> {
	// transactions:accountId:* -> $transactions
	const transactions = await redis.keys(`transactions:${accountId}:*`);
	return transactions.map((transaction) => JSON.parse(transaction));
}

// GET /status
app.get("/status", async (req, res) => {
	try {
		// Ping Redis to check the connection
		await redis.ping();
		res.status(200).json({ status: "ok", redis: "connected" });
	} catch (error) {
		console.error("Redis connection error:", error);
		res
			.status(500)
			.json({ status: "error", message: "Redis connection failed" });
	}
});

// POST /transaction
app.post("/transaction", async (req, res) => {
	const transaction: Transaction = req.body;

	switch (transaction.type) {
		case "deposit":
			// Wrap in {} to prevent scope issues
			{
				const balance = await getBalance(transaction.accountId);
				const newBalance = balance + transaction.amount;
				await setBalance(transaction.accountId, newBalance);
				await addTransaction(transaction.accountId, transaction);
			}
			res.status(200).end();
			break;

		case "withdraw_request": {
			const balance = await getBalance(transaction.accountId);
			if (balance >= transaction.amount) {
				res.status(201).end();
			} else {
				res.status(402).end();
			}
			break;
		}
		case "withdraw": {
			// To prevent race conditions, check the balance again before the transaction
			const balance = await getBalance(transaction.accountId);
			if (balance >= transaction.amount) {
				const newBalance = balance - transaction.amount;
				await setBalance(transaction.accountId, newBalance);
				await addTransaction(transaction.accountId, transaction);
				res.status(200).end();
			} else {
				res.status(402).end();
			}
			break;
		}
		default:
			res
				.status(400)
				.json({ message: "Invalid transaction type", transaction });
	}
});

// GET /account/:accountId
app.get("/account/:accountId", async (req, res) => {
	const { accountId } = req.params;
	const balance = await getBalance(accountId);
	res.status(200).json({ accountId, balance });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
	console.log(`Server is running on port ${PORT}`);
});

export default app;
