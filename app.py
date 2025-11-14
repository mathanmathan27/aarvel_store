from flask import Flask, render_template, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__, template_folder="webpages")

# --------------------------
# GOOGLE SHEETS CONNECTION
# --------------------------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Aarvel Orders").sheet1


# --------------------------
# ADDRESS FORM PAGE
# --------------------------
@app.route("/checkout")
def checkout():
    return render_template("checkout.html")


# --------------------------
# SAVE ADDRESS + OPEN PAYMENT PAGE
# --------------------------
@app.route("/submit_address", methods=["POST"])
def submit_address():
    name = request.form["name"]
    phone = request.form["phone"]
    street = request.form["street"]
    city = request.form["city"]
    state = request.form["state"]
    pincode = request.form["pincode"]
    quantity = request.form["quantity"]

    # PRICE CALCULATION
    if quantity == "250g":
        price = 350
    else:
        price = 700

    # SAVE TO GOOGLE SHEET AS "Pending Payment"
    sheet.append_row([
        name, phone, street, city, state, pincode,
        quantity, price, "Pending", str(datetime.now())
    ])

    # OPEN PAYMENT PAGE
    return render_template(
        "payment.html",
        name=name,
        product="Raw Nendran Banana Powder",
        quantity=quantity,
        price=price
    )


# --------------------------
# PAYMENT SUCCESS PAGE
# --------------------------
@app.route("/payment_success")
def payment_success():

    # UPDATE LAST ORDER TO 'PAID'
    last_row = len(sheet.get_all_values())
    sheet.update_cell(last_row, 9, "Paid")

    return render_template("payment_success.html")


# --------------------------
# RUN APP
# --------------------------
if __name__ == "__main__":
    app.run(debug=True)

