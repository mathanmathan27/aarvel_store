from flask import Flask, render_template, request, redirect, url_for
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid

app = Flask(__name__, template_folder="webpages", static_folder="assets")

# ---------- Google Sheets helper (optional) ----------
# The code below will try to use GOOGLE_CREDENTIALS env or credentials.json.
# If you don't want Google Sheets, you can comment out the sheet writing parts.
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
    # live-site text preserved in template
    return render_template("product_view.html")


@app.route("/checkout")
def checkout():
    # query params: size (250 or 500), price, label
    size = request.args.get("size", "250")
    price = request.args.get("price", "350")
    label = request.args.get("label", "Raw Nendran Banana Powder")
    return render_template("checkout.html", size=size, price=price, label=label)


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

    # detect product size from form
    size = request.form.get("size", "250")
    if size == "500":
        product_name = "Raw Nendran Banana Powder – 500g"
    else:
        product_name = "Raw Nendran Banana Powder – 250g"

    order_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # save to sheet
    if sheet:
        try:
            sheet.append_row([
                order_id, name, phone, street, city, state, pincode,
                quantity, price, "Pending", now
            ])
        except Exception as e:
            print("Failed to write to Google Sheet:", e)

    # ⭐ MUST BE INDENTED — this was your error
    return render_template(
    "payment.html",
    order_id=order_id,
    name=name,
    product_name="Raw Nendran Banana Powder",
    quantity=quantity,
    price=price
)
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os

# ------------------------------
# ANDROID AUTO UPI STATUS
# ------------------------------
@app.route("/upi_callback", methods=["POST"])
def upi_callback():
    data = request.get_json()
    order_id = data.get("order_id")
    status = data.get("status")

    # Save result to file
    with open("upi_status.txt", "a") as f:
        f.write(f"{order_id},{status}\n")

    return jsonify({"ok": True})


@app.route("/payment_result")
def payment_result():
    order_id = request.args.get("order_id")
    status = "PENDING"

    # Read stored statuses
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
    # update Google Sheet status to Paid if possible
    if sheet and order_id:
        try:
            all_values = sheet.get_all_values()
            # search in column 1 for order_id
            row_index = None
            for idx, row in enumerate(all_values, start=1):
                if len(row) > 0 and row[0] == order_id:
                    row_index = idx
                    break
            if row_index:
                # status column is column 10 in our sheet layout
                sheet.update_cell(row_index, 10, "Paid")
        except Exception as e:
            print("Failed to update sheet to Paid:", e)

    return redirect(url_for("payment_success", order_id=order_id))

@app.route("/payment_done")
def payment_done():
    return render_template("payment_done.html")



if __name__ == "__main__":
    app.run(debug=True)
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

    # Your real UPI transaction ID (dummy example)
    real_txn = "ABC123XYZ"

    if user_txn == real_txn:
        return redirect("/payment_done")
    else:
        return redirect("/payment_failed")
