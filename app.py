from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid

app = Flask(__name__, template_folder="webpages", static_folder="assets")

# ---------- Google Sheets helper ----------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

def get_gspread_client():
    env = os.getenv("GOOGLE_CREDENTIALS")
    if env:
        creds_dict = json.loads(env)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    if os.path.exists("credentials.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        return gspread.authorize(creds)
    return None

gclient = None
sheet = None
try:
    gclient = get_gspread_client()
    if gclient:
        sheet = gclient.open("Aarvel Orders").sheet1
except Exception as e:
    print("Google Sheets not available:", e)
    sheet = None

# ---------- Routes ----------

@app.route("/")
def product_view():
    return render_template("product_view.html")

# ---------- Buy page ----------
@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
def buy_product(product_id):
    # Product data
    products = {
        1: {"name": "Raw Nendran Banana Powder", "prices": {"250": 350, "500": 700}},
    }
    product = products.get(product_id)
    if not product:
        return "Product not found", 404

    if request.method == "POST":
        quantity = request.form.get("size")
        price = product["prices"][quantity]
        label = f"{product['name']} ({quantity}g)"
        # Redirect to checkout page with query params
        return redirect(url_for('checkout', size=quantity, price=price, label=label))

    return render_template("buy.html", product=product)

# ---------- Checkout page ----------
@app.route("/checkout")
def checkout():
    size = request.args.get("size", "250")
    price = request.args.get("price", "350")
    label = request.args.get("label", "Raw Nendran Banana Powder")
    return render_template("checkout.html", size=size, price=price, label=label)

# ---------- Submit order ----------
@app.route("/submit_order", methods=["POST"])
def submit_order():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    street = request.form.get("street", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    pincode = request.form.get("pincode", "").strip()
    quantity = request.form.get("quantity", "").strip()
    price = request.form.get("price", "").strip()

    size = request.form.get("size", "250")
    product_name = f"Raw Nendran Banana Powder – {size}g"

    order_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if sheet:
        try:
            sheet.append_row([
                order_id, name, phone, street, city, state, pincode,
                quantity, price, "Pending", now
            ])
        except Exception as e:
            print("Failed to write to Google Sheet:", e)

    return render_template(
        "payment.html",
        order_id=order_id,
        name=name,
        product_name=product_name,
        quantity=quantity,
        price=price
    )

# ---------- UPI and payment callbacks ----------
@app.route("/upi_callback", methods=["POST"])
def upi_callback():
    data = request.get_json()
    order_id = data.get("order_id")
    status = data.get("status")
    with open("upi_status.txt", "a") as f:
        f.write(f"{order_id},{status}\n")
    return jsonify({"ok": True})

@app.route("/payment_result")
def payment_result():
    order_id = request.args.get("order_id")
    status = "PENDING"
    if os.path.exists("upi_status.txt"):
        with open("upi_status.txt") as f:
            lines = f.readlines()
            for line in lines:
                oid, st = line.strip().split(",")
                if oid == order_id:
                    status = st
    if status == "SUCCESS":
        return render_template("payment_success.html", order_id=order_id)
    elif status in ["FAILURE", "CANCELLED"]:
        return render_template("payment_failed.html", order_id=order_id)
    else:
        return render_template("payment_pending.html", order_id=order_id)

@app.route("/confirm_paid", methods=["POST"])
def confirm_paid():
    order_id = request.form.get("order_id", "")
    if sheet and order_id:
        try:
            all_values = sheet.get_all_values()
            row_index = None
            for idx, row in enumerate(all_values, start=1):
                if len(row) > 0 and row[0] == order_id:
                    row_index = idx
                    break
            if row_index:
                sheet.update_cell(row_index, 10, "Paid")
        except Exception as e:
            print("Failed to update sheet to Paid:", e)
    return redirect(url_for("payment_success", order_id=order_id))

@app.route("/payment_done")
def payment_done():
    return render_template("payment_done.html")

@app.route("/manual_paid", methods=["POST"])
def manual_paid():
    order_id = request.form.get("order_id")
    file = request.files.get("screenshot")
    if file:
        filepath = os.path.join("uploads", f"{order_id}.jpg")
        file.save(filepath)
    return render_template("payment_pending.html", order_id=order_id)

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    user_txn = request.form.get("txn_id")
    real_txn = "ABC123XYZ"
    if user_txn == real_txn:
        return redirect("/payment_done")
    else:
        return redirect("/payment_failed")


if __name__ == "__main__":
    app.run(debug=True)
