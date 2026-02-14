from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3

app = FastAPI()
DB = "bank.db"

def get_db():
    return sqlite3.connect(DB)

def get_user_role(user_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid user")

    return row[0]


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

    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "user_id": user[0],
            "role": user[1]
        }
    }


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

    return {
        "success": True,
        "message": "Balance fetched successfully",
        "data": {
            "balance": bal[0]
        }
    }


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

@app.get("/admin/customers")
def list_customers(user_id: int):
    # Step 1: Verify role
    role = get_user_role(user_id)

    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    conn = get_db()
    cur = conn.cursor()

    # Step 2: Fetch users + account balance
    cur.execute("""
    SELECT users.id, users.username, users.role, accounts.balance
    FROM users
    LEFT JOIN accounts ON users.id = accounts.user_id
    """)

    rows = cur.fetchall()
    conn.close()

    return {
        "success": True,
        "message": "Customers fetched successfully",
        "data": [
            {
                "id": r[0],
                "username": r[1],
                "role": r[2],
                "balance": r[3] if r[3] is not None else 0
            }
            for r in rows
        ]
    }

@app.delete("/admin/delete-user")
def delete_user(admin_id: int, user_id: int):
    # Verify admin
    role = get_user_role(admin_id)

    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if user_id == admin_id:
        raise HTTPException(status_code=400, detail="Admin cannot delete self")

    conn = get_db()
    cur = conn.cursor()

    # Delete account first
    cur.execute("DELETE FROM accounts WHERE user_id=?", (user_id,))
    
    # Delete user
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "User deleted successfully",
        "data": None
    }
