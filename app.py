"""Kirana Shop Billing System - main Flask application.

Run with:  python app.py   then open http://127.0.0.1:5000
"""
import csv
import io
import os
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, Response, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from db import close_db, get_db, init_db

# ---------- Settings (change these for your shop) ----------
SHOP_NAME = "Shree Kirana Store"
SHOP_ADDRESS = "Main Market, Patna, Bihar"
SHOP_PHONE = "98XXXXXXXX"
SHOP_GSTIN = ""   # optional

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-real-use")
app.teardown_appcontext(close_db)


# ---------- Login protection ----------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify(error="Please login again"), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Only admin can open that page.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_globals():
    return dict(SHOP_NAME=SHOP_NAME, SHOP_ADDRESS=SHOP_ADDRESS,
                SHOP_PHONE=SHOP_PHONE, SHOP_GSTIN=SHOP_GSTIN)


def num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------- Login / Logout ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_db().execute("SELECT * FROM users WHERE username=?",
                                (request.form.get("username", "").strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session.update(user_id=user["id"], username=user["username"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Wrong username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Dashboard ----------
@app.route("/")
@login_required
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    t = db.execute("SELECT COALESCE(SUM(total),0) s, COUNT(*) c FROM sales WHERE date(created_at)=?",
                   (today,)).fetchone()
    month_start = date.today().replace(day=1).isoformat()
    m = db.execute("SELECT COALESCE(SUM(total),0) s FROM sales WHERE date(created_at)>=?",
                   (month_start,)).fetchone()
    low = db.execute("SELECT * FROM products WHERE stock <= min_stock ORDER BY stock LIMIT 8").fetchall()
    low_count = db.execute("SELECT COUNT(*) FROM products WHERE stock <= min_stock").fetchone()[0]
    products_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    # last 7 days (fill missing days with 0)
    start = (date.today() - timedelta(days=6)).isoformat()
    rows = db.execute("SELECT date(created_at) d, SUM(total) s FROM sales "
                      "WHERE date(created_at)>=? GROUP BY d", (start,)).fetchall()
    by_day = {r["d"]: r["s"] for r in rows}
    labels, values = [], []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        values.append(round(by_day.get(d.isoformat(), 0), 2))

    top = db.execute("SELECT name, SUM(qty) q, SUM(qty*price) amt FROM sale_items si "
                     "JOIN sales s ON s.id=si.sale_id WHERE date(s.created_at)>=? "
                     "GROUP BY name ORDER BY amt DESC LIMIT 5", (start,)).fetchall()
    recent = db.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 5").fetchall()
    return render_template("dashboard.html", today_total=t["s"], today_bills=t["c"],
                           month_total=m["s"], low=low, low_count=low_count,
                           products_count=products_count, labels=labels, values=values,
                           top=top, recent=recent)


# ---------- Products ----------
@app.route("/products")
@login_required
def products():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        rows = db.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ? OR category LIKE ? "
                          "ORDER BY name", (like, like, like)).fetchall()
    else:
        rows = db.execute("SELECT * FROM products ORDER BY name").fetchall()
    return render_template("products.html", products=rows, q=q)


def product_from_form():
    f = request.form
    return dict(
        barcode=f.get("barcode", "").strip() or None,
        name=f.get("name", "").strip(),
        category=f.get("category", "").strip() or "General",
        unit=f.get("unit", "").strip() or "pcs",
        cost_price=num(f.get("cost_price")),
        price=num(f.get("price")),
        gst=num(f.get("gst")),
        stock=num(f.get("stock")),
        min_stock=num(f.get("min_stock"), 5),
    )


@app.route("/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def product_add():
    if request.method == "POST":
        p = product_from_form()
        if not p["name"] or p["price"] <= 0:
            flash("Name and a price greater than 0 are required.", "error")
            return render_template("product_form.html", p=p, title="Add Product")
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO products (barcode,name,category,unit,cost_price,price,gst,stock,min_stock)"
                " VALUES (:barcode,:name,:category,:unit,:cost_price,:price,:gst,:stock,:min_stock)", p)
            if not p["barcode"]:  # auto-generate our own barcode
                db.execute("UPDATE products SET barcode=? WHERE id=?", (f"KR{cur.lastrowid:06d}", cur.lastrowid))
            db.commit()
        except sqlite3.IntegrityError:
            flash("This barcode already exists for another product.", "error")
            return render_template("product_form.html", p=p, title="Add Product")
        flash("Product added.", "ok")
        return redirect(url_for("products"))
    return render_template("product_form.html", p={}, title="Add Product")


@app.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def product_edit(pid):
    db = get_db()
    existing = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not existing:
        flash("Product not found.", "error")
        return redirect(url_for("products"))
    if request.method == "POST":
        p = product_from_form()
        p["id"] = pid
        if not p["name"] or p["price"] <= 0:
            flash("Name and a price greater than 0 are required.", "error")
            return render_template("product_form.html", p=p, title="Edit Product")
        try:
            db.execute("UPDATE products SET barcode=:barcode, name=:name, category=:category, unit=:unit,"
                       " cost_price=:cost_price, price=:price, gst=:gst, stock=:stock, min_stock=:min_stock"
                       " WHERE id=:id", p)
            db.commit()
        except sqlite3.IntegrityError:
            flash("This barcode already exists for another product.", "error")
            return render_template("product_form.html", p=p, title="Edit Product")
        flash("Product updated.", "ok")
        return redirect(url_for("products"))
    return render_template("product_form.html", p=existing, title="Edit Product")


@app.post("/products/<int:pid>/delete")
@login_required
@admin_required
def product_delete(pid):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (pid,))
    db.commit()
    flash("Product deleted (old bills are kept safely).", "ok")
    return redirect(url_for("products"))


@app.route("/labels")
@login_required
@admin_required
def labels():
    """Printable barcode stickers for products."""
    rows = get_db().execute("SELECT name, barcode, price FROM products WHERE barcode IS NOT NULL "
                            "ORDER BY name").fetchall()
    return render_template("labels.html", products=rows)


# ---------- Product lookup APIs used by the billing screen ----------
@app.get("/api/product")
@login_required
def api_product():
    code = request.args.get("barcode", "").strip()
    p = get_db().execute("SELECT id,barcode,name,unit,price,stock FROM products WHERE barcode=?",
                         (code,)).fetchone()
    if not p:
        return jsonify(error="Not found"), 404
    return jsonify(dict(p))


@app.get("/api/search")
@login_required
def api_search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    rows = get_db().execute("SELECT id,barcode,name,unit,price,stock FROM products "
                            "WHERE name LIKE ? OR barcode LIKE ? ORDER BY name LIMIT 8",
                            (f"%{q}%", f"%{q}%")).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------- Billing ----------
@app.route("/billing")
@login_required
def billing():
    return render_template("billing.html")


@app.post("/api/checkout")
@login_required
def checkout():
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if not items:
        return jsonify(error="Cart is empty."), 400

    payment = data.get("payment_method", "Cash")
    if payment not in ("Cash", "UPI", "Card", "Credit"):
        payment = "Cash"

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")  # lock so two cashiers cannot sell the same last item
        lines, subtotal, tax_raw = [], 0.0, 0.0
        for it in items:
            qty = num(it.get("qty"))
            p = db.execute("SELECT * FROM products WHERE id=?", (it.get("id"),)).fetchone()
            if not p or qty <= 0:
                raise ValueError("Invalid item in cart.")
            if p["stock"] < qty:
                raise ValueError(f"Not enough stock for {p['name']} (only {p['stock']:g} left).")
            line_total = p["price"] * qty              # server uses DB price, not browser price
            subtotal += line_total
            tax_raw += line_total * p["gst"] / (100 + p["gst"])   # price already includes GST
            lines.append((p, qty))

        discount = min(max(num(data.get("discount")), 0), subtotal)
        tax = tax_raw * ((subtotal - discount) / subtotal) if subtotal else 0
        total = round(subtotal - discount, 2)

        cur = db.execute(
            "INSERT INTO sales (invoice_no, customer_name, payment_method, subtotal, discount, tax, total, cashier_id)"
            " VALUES ('TMP',?,?,?,?,?,?,?)",
            ((data.get("customer_name") or "").strip() or "Walk-in", payment,
             round(subtotal, 2), round(discount, 2), round(tax, 2), total, session["user_id"]))
        sale_id = cur.lastrowid
        db.execute("UPDATE sales SET invoice_no=? WHERE id=?", (f"INV-{sale_id:05d}", sale_id))
        for p, qty in lines:
            db.execute("INSERT INTO sale_items (sale_id,product_id,name,qty,price,cost,gst) VALUES (?,?,?,?,?,?,?)",
                       (sale_id, p["id"], p["name"], qty, p["price"], p["cost_price"], p["gst"]))
            db.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, p["id"]))
        db.commit()
    except ValueError as e:
        db.rollback()
        return jsonify(error=str(e)), 400
    except Exception:
        db.rollback()
        return jsonify(error="Something went wrong. Bill not saved."), 500
    return jsonify(ok=True, sale_id=sale_id, url=url_for("invoice", sale_id=sale_id))


@app.route("/invoice/<int:sale_id>")
@login_required
def invoice(sale_id):
    db = get_db()
    sale = db.execute("SELECT s.*, u.username cashier FROM sales s LEFT JOIN users u ON u.id=s.cashier_id "
                      "WHERE s.id=?", (sale_id,)).fetchone()
    if not sale:
        flash("Bill not found.", "error")
        return redirect(url_for("sales"))
    items = db.execute("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)).fetchall()
    return render_template("invoice.html", sale=sale, items=items)


@app.route("/sales")
@login_required
def sales():
    d = request.args.get("date", date.today().isoformat())
    rows = get_db().execute("SELECT s.*, u.username cashier FROM sales s LEFT JOIN users u ON u.id=s.cashier_id "
                            "WHERE date(s.created_at)=? ORDER BY s.id DESC", (d,)).fetchall()
    total = sum(r["total"] for r in rows)
    return render_template("sales.html", sales=rows, day=d, total=total)


# ---------- Reports ----------
def report_data(start, end):
    db = get_db()
    p = (start, end)
    summary = db.execute("SELECT COUNT(*) bills, COALESCE(SUM(total),0) revenue, COALESCE(SUM(discount),0) discount,"
                         " COALESCE(SUM(tax),0) tax FROM sales WHERE date(created_at) BETWEEN ? AND ?", p).fetchone()
    gross = db.execute("SELECT COALESCE(SUM((si.price-si.cost)*si.qty),0) FROM sale_items si "
                       "JOIN sales s ON s.id=si.sale_id WHERE date(s.created_at) BETWEEN ? AND ?", p).fetchone()[0]
    profit = gross - summary["discount"]
    daily = db.execute("SELECT date(created_at) day, COUNT(*) bills, SUM(total) total FROM sales "
                       "WHERE date(created_at) BETWEEN ? AND ? GROUP BY day ORDER BY day", p).fetchall()
    payments = db.execute("SELECT payment_method m, COUNT(*) c, SUM(total) total FROM sales "
                          "WHERE date(created_at) BETWEEN ? AND ? GROUP BY m", p).fetchall()
    top = db.execute("SELECT si.name, SUM(si.qty) qty, SUM(si.qty*si.price) amount, "
                     "SUM((si.price-si.cost)*si.qty) profit FROM sale_items si JOIN sales s ON s.id=si.sale_id "
                     "WHERE date(s.created_at) BETWEEN ? AND ? GROUP BY si.name ORDER BY amount DESC LIMIT 10",
                     p).fetchall()
    cats = db.execute("SELECT COALESCE(pr.category,'Deleted items') cat, SUM(si.qty*si.price) amount "
                      "FROM sale_items si JOIN sales s ON s.id=si.sale_id "
                      "LEFT JOIN products pr ON pr.id=si.product_id "
                      "WHERE date(s.created_at) BETWEEN ? AND ? GROUP BY cat ORDER BY amount DESC", p).fetchall()
    stock_value = db.execute("SELECT COALESCE(SUM(stock*cost_price),0) FROM products").fetchone()[0]
    return summary, profit, daily, payments, top, cats, stock_value


@app.route("/reports")
@login_required
@admin_required
def reports():
    end = request.args.get("end", date.today().isoformat())
    start = request.args.get("start", (date.today() - timedelta(days=29)).isoformat())
    summary, profit, daily, payments, top, cats, stock_value = report_data(start, end)
    return render_template("reports.html", start=start, end=end, summary=summary, profit=profit,
                           daily=daily, payments=payments, top=top, cats=cats, stock_value=stock_value)


@app.route("/reports/export.csv")
@login_required
@admin_required
def export_csv():
    end = request.args.get("end", date.today().isoformat())
    start = request.args.get("start", (date.today() - timedelta(days=29)).isoformat())
    rows = get_db().execute("SELECT invoice_no, created_at, customer_name, payment_method, subtotal, discount, tax,"
                            " total FROM sales WHERE date(created_at) BETWEEN ? AND ? ORDER BY id", (start, end))
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Invoice", "Date/Time", "Customer", "Payment", "Subtotal", "Discount", "GST included", "Total"])
    for r in rows:
        w.writerow(list(r))
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=sales_{start}_to_{end}.csv"})


# ---------- Users (admin only) ----------
@app.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    db = get_db()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "cashier")
        if not username or len(password) < 6 or role not in ("admin", "cashier"):
            flash("Enter a username and a password of at least 6 characters.", "error")
        else:
            try:
                db.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                           (username, generate_password_hash(password), role))
                db.commit()
                flash("User added.", "ok")
            except sqlite3.IntegrityError:
                flash("That username is already taken.", "error")
        return redirect(url_for("users"))
    return render_template("users.html", users=db.execute("SELECT id,username,role FROM users").fetchall())


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        new = request.form.get("new", "")
        if not check_password_hash(user["password_hash"], request.form.get("old", "")):
            flash("Old password is wrong.", "error")
        elif len(new) < 6:
            flash("New password must be at least 6 characters.", "error")
        else:
            db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new), user["id"]))
            db.commit()
            flash("Password changed.", "ok")
            return redirect(url_for("dashboard"))
    return render_template("change_password.html")


init_db()

if __name__ == "__main__":
    # host 0.0.0.0 lets other devices on your shop Wi-Fi open the app too.
    # debug is OFF on purpose: debug mode must never be exposed on a network.
    app.run(host="0.0.0.0", port=5000, debug=False)
