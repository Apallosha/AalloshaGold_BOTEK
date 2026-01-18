import sqlite3

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    ref_by INTEGER,
    banned INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS refs (
    referrer INTEGER,
    referral INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    channel TEXT,
    reward INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS completed_tasks (
    user_id INTEGER,
    task_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdraws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    full_amount REAL,
    photo TEXT,
    status TEXT DEFAULT 'pending'
)
""")

conn.commit()

