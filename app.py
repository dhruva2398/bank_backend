from fastapi import FastAPI
import logging
import os
import sqlite3

# -----------------------
# APPLICATION SETUP
# -----------------------
app = FastAPI()

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Logging configuration
logging.basicConfig(
    filename="logs/bank.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -----------------------
# DATABASE SETUP
# -----------------------
conn = sqlite3.connect("bank.db", check_same_thread=False)
cursor = conn.cursor()

# Create customers table
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")

# Create accounts table
cursor.execute("""
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    balance INTEGER
)
""")

conn.commit()

# -----------------------
# APIs
# -----------------------

# Health Check
@app.get("/")
def health_check():
    logging.info("Health check called")
    return {"status": "Bank backend is running"}

# Create Customer
@app.post("/customers")
def create_customer(name: str):
    cursor.execute("INSERT INTO customers (name) VALUES (?)", (name,))
    conn.commit()
    logging.info(f"Customer created: {name}")
    return {"message": "Customer created successfully"}

# Get All Customers
@app.get("/customers")
def get_customers():
    cursor.execute("SELECT * FROM customers")
    rows = cursor.fetchall()
    logging.info("Fetched all customers")
    return {
        "customers": [
            {"id": row[0], "name": row[1]} for row in rows
        ]
    }

# Create Account
@app.post("/accounts")
def create_account(customer_id: int):
    cursor.execute(
        "INSERT INTO accounts (customer_id, balance) VALUES (?, ?)",
        (customer_id, 0)
    )
    conn.commit()
    logging.info(f"Account created for customer {customer_id}")
    return {"message": "Account created successfully"}

# Get All Accounts
@app.get("/accounts")
def get_accounts():
    cursor.execute("SELECT * FROM accounts")
    rows = cursor.fetchall()
    logging.info("Fetched all accounts")
    return {
        "accounts": [
            {
                "account_id": row[0],
                "customer_id": row[1],
                "balance": row[2]
            }
            for row in rows
        ]
    }

# Deposit Money
@app.post("/deposit")
def deposit(account_id: int, amount: int):
    cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
    row = cursor.fetchone()

    if not row:
        return {"error": "Account not found"}

    new_balance = row[0] + amount
    cursor.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?",
        (new_balance, account_id)
    )
    conn.commit()

    logging.info(f"Deposited {amount} to account {account_id}")
    return {
        "message": "Deposit successful",
        "account_id": account_id,
        "balance": new_balance
    }

# Withdraw Money
@app.post("/withdraw")
def withdraw(account_id: int, amount: int):
    cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
    row = cursor.fetchone()

    if not row:
        return {"error": "Account not found"}

    if row[0] < amount:
        logging.warning(f"Insufficient funds for account {account_id}")
        return {"error": "Insufficient balance"}

    new_balance = row[0] - amount
    cursor.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?",
        (new_balance, account_id)
    )
    conn.commit()

    logging.info(f"Withdrawn {amount} from account {account_id}")
    return {
        "message": "Withdrawal successful",
        "account_id": account_id,
        "balance": new_balance
    }

# Balance Enquiry
@app.get("/balance")
def get_balance(account_id: int):
    cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
    row = cursor.fetchone()

    if not row:
        return {"error": "Account not found"}

    logging.info(f"Balance checked for account {account_id}")
    return {
        "account_id": account_id,
        "balance": row[0]
    }
