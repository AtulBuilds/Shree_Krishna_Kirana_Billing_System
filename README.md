# Kirana Shop Billing System

A website for a grocery shop: login, dashboard, barcode billing, printable invoices, stock alerts, barcode labels and reports.
Built with **Python (Flask)** + **HTML, CSS, JavaScript**. Data is stored in one file: `shop.db` (SQLite).

## 1. Folder structure

```
kirana-billing/
├── app.py              <- the brain: all pages and logic (Python)
├── db.py               <- creates the database tables + sample data
├── requirements.txt    <- list of Python packages needed (only Flask)
├── shop.db             <- created automatically on first run (your data!)
├── templates/          <- HTML pages
│   ├── base.html           (menu + common layout, other pages build on it)
│   ├── _icons.html         (the small icons used in menus and buttons)
│   ├── login.html
│   ├── dashboard.html
│   ├── products.html / product_form.html
│   ├── billing.html        (the cash counter screen)
│   ├── invoice.html        (printable bill)
│   ├── sales.html          (old bills by date)
│   ├── reports.html
│   ├── labels.html         (barcode stickers)
│   ├── users.html / change_password.html
└── static/
    ├── css/style.css       (colors, layout, light + dark theme)
    └── js/billing.js       (cart + barcode scanning in the browser)
    └── js/charts.js        (chart colours/styling; shows simple bars when offline)
```

## 2. Setup (one time)

You need Python 3.9 or newer (check with `python --version`).

**Windows (Command Prompt):**
```
cd kirana-billing
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / Mac:**
```
cd kirana-billing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Run

```
python app.py
```
Open **http://127.0.0.1:5000** in Chrome.

First login: username `admin`, password `admin123`.
**Change this password first** (menu -> Change Password).

To use it from a phone or second computer on the same Wi-Fi, open `http://<your-PC-IP>:5000`.

Stop the server with `Ctrl + C`.

## 4. How to use

1. **Products** -> add your items (barcode, price, GST %, stock). Leave barcode empty to auto-create one.
2. **Barcode Labels** -> print stickers for loose items that have no barcode.
3. **New Bill** -> click the big box, scan with a USB barcode scanner (it types the code and presses Enter). You can also type a name. Press **F9** to save and print.
4. **Dashboard** -> today's sales, 7-day chart, low-stock list.
5. **Reports** (admin) -> pick dates: revenue, profit, top items, category sales, payment split, CSV download.
6. **Users** (admin) -> create cashier logins. Cashiers can bill but cannot see reports or edit products.

## 5. How the main parts work (simple)

- **Browser (JavaScript)** keeps the cart. When you press Save, it sends item ids and quantities to Python.
- **Python (`/api/checkout`)** looks up real prices from the database (it never trusts prices from the browser), checks stock, saves the bill, and reduces stock - all in one safe step. If anything fails, nothing is saved.
- **Prices include GST.** The invoice shows how much of the total was GST.
- **Profit** = (selling price - cost price) x quantity - discounts.

## 6. Before real shop use

- Change `SHOP_NAME`, `SHOP_ADDRESS`, `SHOP_PHONE` at the top of `app.py`.
- Set a strong secret key: `set SECRET_KEY=anything-long-and-random` (Windows) or `export SECRET_KEY=...` (Linux/Mac) before running.
- **Backup:** copy `shop.db` to a pendrive/Google Drive every day. That file is all your data.
- Charts and barcode drawing load libraries from the internet (Chart.js, JsBarcode). Billing itself works offline.

## 7. Ideas to add next

Customer udhaar (credit) ledger, bill cancel/return, purchase entry (add stock from supplier), WhatsApp bill sharing, CSRF protection, deploy on a small server with `gunicorn`.
