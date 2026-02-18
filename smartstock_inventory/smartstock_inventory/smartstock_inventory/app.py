from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import smtplib
from email.mime.text import MIMEText
import secrets
import random

app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = "smartstock_secret_key"

# DATABASE
client = MongoClient("mongodb://localhost:27017/")
db = client["smartstock"]

# MAIN USERS COLLECTION
collection = db["users"]

# TEMP OTP STORAGE (NO DATABASE)
otp_storage = {}

# EMAIL CONFIG
EMAIL_ADDRESS = "smartstockinventory13@gmail.com"
EMAIL_PASSWORD = "mqba dccc kkls xnbs"


# ---------------- PAGE ROUTES ----------------

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/reset-password-page")
def reset_password_page():
    token = request.args.get("token")
    return render_template("reset_password.html", token=token)


# ---------------- TOKEN DECORATOR ----------------

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]

        if not token:
            return jsonify({"message": "Token missing"}), 401

        try:
            data = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )
            current_user = data
        except:
            return jsonify({"message": "Token invalid"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# ---------------- SEND OTP ----------------

@app.route("/send-otp", methods=["POST"])
def send_otp():

    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"message": "Email required"}), 400

    otp = str(random.randint(100000, 999999))
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)

    otp_storage[email] = {
        "otp": otp,
        "otp_expiry": expiry
    }

    try:
        msg = MIMEText(f"Your SmartStock OTP is: {otp}\n\nValid for 5 minutes.")
        msg["Subject"] = "SmartStock OTP Verification"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        server.quit()

        return jsonify({"message": "OTP sent successfully"}), 200

    except Exception as e:
        print("OTP email error:", e)
        return jsonify({"message": "Server error while sending OTP"}), 500


# ---------------- VERIFY OTP ----------------

@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return jsonify({"message": "Missing data"}), 400

    user = otp_storage.get(email)

    if not user:
        return jsonify({"message": "OTP not requested"}), 404

    if user.get("otp") != otp:
        return jsonify({"message": "Invalid OTP"}), 400

    if datetime.datetime.utcnow() > user.get("otp_expiry"):
        del otp_storage[email]
        return jsonify({"message": "OTP expired"}), 400

    del otp_storage[email]

    return jsonify({"message": "OTP verified"}), 200


# ---------------- REGISTER ----------------

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not username or not email or not password or not role:
        return jsonify({"message": "Missing fields"}), 400

    if collection.find_one({"username": username}):
        return jsonify({"message": "Username already exists"}), 400

    if collection.find_one({"email": email}):
        return jsonify({"message": "Email already exists"}), 400

    hashed_password = generate_password_hash(password)

    collection.insert_one({
        "username": username,
        "email": email,
        "password": hashed_password,
        "role": role,
        "contactNumber": data.get("contactNumber"),
        "shopAddress": data.get("shopAddress"),
        "gstin": data.get("gstin"),
        "city": data.get("city"),
        "state": data.get("state"),
        "pincode": data.get("pincode")
    })

    return jsonify({"message": "Registration successful"}), 201


# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Missing credentials"}), 400

    user = collection.find_one({
        "$or": [{"username": username}, {"email": username}]
    })

    if not user:
        return jsonify({"message": "Account does not exist"}), 401

    if not check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid password"}), 401

    token = jwt.encode({
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return jsonify({
        "message": "Login successful",
        "token": token,
        "role": user["role"]
    })


# ---------------- FORGOT PASSWORD ----------------

@app.route("/forgot-password", methods=["POST"])
def forgot_password():

    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"message": "Email required"}), 400

    user = collection.find_one({"email": email})
    if not user:
        return jsonify({"message": "Email not registered"}), 404

    reset_token = secrets.token_urlsafe(32)
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

    collection.update_one(
        {"email": email},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiry": expiry
        }}
    )

    reset_link = f"http://127.0.0.1:5000/reset-password-page?token={reset_token}"

    try:
        msg = MIMEText(f"""
Click below to reset password:

{reset_link}

Valid for 15 minutes.
""")

        msg["Subject"] = "SmartStock Password Reset"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        server.quit()

        return jsonify({"message": "Password reset link sent"}), 200

    except Exception as e:
        print("Email error:", e)
        return jsonify({"message": "Failed to send email"}), 500


# ---------------- RESET PASSWORD (FIXED) ----------------

@app.route("/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json()

    # Accept both newPassword and newpassword from frontend
    token = data.get("token")
    new_password = data.get("newPassword") or data.get("newpassword")

    if not token or not new_password:
        return jsonify({"message": "Missing data"}), 400

    user = collection.find_one({"reset_token": token})

    if not user:
        return jsonify({"message": "Invalid token"}), 400

    # Safe expiry check
    expiry = user.get("reset_token_expiry")
    if not expiry or datetime.datetime.utcnow() > expiry:
        return jsonify({"message": "Token expired"}), 400

    hashed_password = generate_password_hash(new_password)

    collection.update_one(
        {"reset_token": token},
        {
            "$set": {"password": hashed_password},
            "$unset": {"reset_token": 1, "reset_token_expiry": 1}
        }
    )

    return jsonify({"message": "Password updated successfully"}), 200


# ---------------- ADMIN VIEW USERS ----------------

@app.route("/admin/users", methods=["GET"])
@token_required
def get_users(current_user):

    if current_user["role"] != "admin":
        return jsonify({"message": "Admin access required"}), 403

    users = list(collection.find({}, {"_id": 0, "username": 1, "role": 1}))
    return jsonify({"users": users})


if __name__ == "__main__":
    app.run(debug=True)
