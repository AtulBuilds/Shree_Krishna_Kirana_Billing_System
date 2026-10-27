"""Database helpers. SQLite is a simple database stored in ONE file (shop.db)."""
import os
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'cashier'      -- 'admin' or 'cashier'
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE,
    name TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    unit TEXT DEFAULT 'pcs',                  -- pcs, kg, litre, packet ...
    cost_price REAL NOT NULL DEFAULT 0,       -- what you paid
    price REAL NOT NULL,                      -- what customer pays (includes GST)
    gst REAL NOT NULL DEFAULT 0,              -- GST percent, e.g. 5
    stock REAL NOT NULL DEFAULT 0,
    min_stock REAL NOT NULL DEFAULT 5         -- warn when stock <= this
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    customer_name TEXT,
    payment_method TEXT NOT NULL DEFAULT 'Cash',
    subtotal REAL NOT NULL,
    discount REAL NOT NULL DEFAULT 0,
    tax REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL,
    cashier_id INTEGER
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL REFERENCES sales(id),
    product_id INTEGER,
    name TEXT NOT NULL,
    qty REAL NOT NULL,
    price REAL NOT NULL,
    cost REAL NOT NULL DEFAULT 0,
    gst REAL NOT NULL DEFAULT 0
);
"""

SAMPLE_PRODUCTS = [
    ("8901000000011", "Tata Salt 1kg", "Staples", "packet", 22, 28, 0, 40, 10),
    ("8901000000028", "Aashirvaad Atta 5kg", "Staples", "packet", 215, 245, 0, 25, 5),
    ("8901000000035", "Fortune Oil 1L", "Oil", "packet", 120, 138, 5, 30, 8),
    ("8901000000042", "Parle-G Biscuit", "Snacks", "pcs", 8, 10, 18, 100, 20),
    ("8901000000059", "Maggi Noodles", "Snacks", "pcs", 12, 14, 12, 80, 20),
    ("8901000000066", "Tea Powder 250g", "Beverages", "packet", 70, 85, 5, 3, 5),
    ("8901000000073", "Sugar (loose)", "Staples", "kg", 38, 46, 0, 60, 10),
]


def get_db():
    """One connection per request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables. On the very first run, add an admin user + sample products."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            ("admin", generate_password_hash("admin123"), "admin"),
        )
        conn.executemany(
            "INSERT INTO products (barcode,name,category,unit,cost_price,price,gst,stock,min_stock)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            SAMPLE_PRODUCTS,
        )
    conn.commit()
    conn.close()
