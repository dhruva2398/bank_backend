from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3

app = FastAPI()
DB = "bank.db"

def get_db():
    return sqlite3.connect(DB)

# ---------------- DB INIT ----------------
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        balance REAL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Default admin
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES (NULL,'admin','admin','admin')")

    conn.commit()
    conn.close()

init_db()

# ---------------- FRONTEND ----------------
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/", response_class=HTMLResponse)
def login_page():
    return open("frontend/login.html").read()

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return open("frontend/admin.html").read()

@app.get("/customer", response_class=HTMLResponse)
def customer_page():
    return open("frontend/customer.html").read()

# ---------------- AUTH ----------------
@app.post("/login")
def login(username: str, password: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"user_id": user[0], "role": user[1]}

# ---------------- ADMIN ----------------
@app.post("/admin/create-user")
def create_user(username: str, password: str):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users VALUES (NULL,?,?,?)", (username, password, "customer"))
        user_id = cur.lastrowid
        cur.execute("INSERT INTO accounts VALUES (NULL,?,0)", (user_id,))
        conn.commit()
    except:
        raise HTTPException(status_code=400, detail="User exists")
    finally:
        conn.close()

    return {"message": "Customer created"}

# ---------------- CUSTOMER ----------------
@app.get("/balance")
def balance(user_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM accounts WHERE user_id=?", (user_id,))
    bal = cur.fetchone()
    conn.close()

    if not bal:
        raise HTTPException(status_code=404, detail="Account not found")

    return {"balance": bal[0]}

@app.post("/deposit")
def deposit(user_id: int, amount: float):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE accounts SET balance=balance+? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()
    return {"message": "Deposit successful"}

@app.post("/withdraw")
def withdraw(user_id: int, amount: float):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM accounts WHERE user_id=?", (user_id,))
    bal = cur.fetchone()

    if bal[0] < amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    cur.execute("UPDATE accounts SET balance=balance-? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()
    return {"message": "Withdrawal successful"}
