-- init.sql

-- Account Table to hold balances
CREATE TABLE accounts
(
    id      TEXT PRIMARY KEY,
    balance DECIMAL(10, 2) NOT NULL
);

-- Transaction Table to log all transactions
CREATE TABLE transactions
(
    id         TEXT PRIMARY KEY,
    account_id TEXT REFERENCES accounts (id) ON DELETE CASCADE,
    type       TEXT           NOT NULL,
    amount     DECIMAL(10, 2) NOT NULL,
    timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger function to create account if it does not exist
CREATE
OR REPLACE FUNCTION ensure_account_exists()
RETURNS TRIGGER AS $$
BEGIN
    IF
NOT EXISTS (SELECT 1 FROM accounts WHERE id = NEW.account_id) THEN
        INSERT INTO accounts (id, balance) VALUES (NEW.account_id, 0);
END IF;

RETURN NEW;
END;
$$
LANGUAGE plpgsql;

-- Trigger to call the function before inserting into transactions
CREATE TRIGGER init_account_before_transaction
    BEFORE INSERT
    ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION ensure_account_exists();
