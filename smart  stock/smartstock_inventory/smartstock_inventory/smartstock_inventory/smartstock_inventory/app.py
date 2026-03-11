from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import smtplib
from email.mime.text import MIMEText
import random
import json
from bson import ObjectId
import os
import secrets
import time
import threading
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure

app = Flask(__name__, template_folder='templates')
CORS(app)

app.config["SECRET_KEY"] = "smartstock_secret_key"

# Global connection state
connection_state = {
    'client': None,
    'db': None,
    'is_connected': False,
    'last_check': None,
    'retry_count': 0,
    'max_retries': 5,
    'lock': threading.Lock()
}

def get_connection_string():
    """Get MongoDB connection string with fallback options"""
    return "mongodb://localhost:27017/"

def create_mongo_client():
    """Create MongoDB client with enhanced connection settings"""
    return MongoClient(
        get_connection_string(),
        maxPoolSize=100,  # Increased pool size
        minPoolSize=10,   # Minimum pool size
        maxIdleTimeMS=30000,  # Close idle connections after 30s
        serverSelectionTimeoutMS=10000,  # Increased timeout
        socketTimeoutMS=45000,  # Increased socket timeout
        connectTimeoutMS=10000,  # Increased connect timeout
        retryWrites=True,
        retryReads=True,
        w="majority",
        readPreference="secondaryPreferred",
        heartbeatFrequencyMS=10000,  # Check connection health every 10s
        appName="smartstock_inventory"  # Application identification
    )

def test_connection(mongo_client):
    """Test MongoDB connection with comprehensive checks"""
    try:
        # Basic ping test
        mongo_client.admin.command('ping')
        
        # Test database access
        mongo_client['smartstock'].list_collection_names()
        
        # Test write operation
        test_collection = mongo_client['smartstock']['connection_test']
        test_collection.insert_one({'test': True, 'timestamp': datetime.datetime.now()})
        test_collection.delete_many({'test': True})
        
        return True, "Connection successful"
    except ConnectionFailure as e:
        return False, f"Connection failed: {str(e)}"
    except ServerSelectionTimeoutError as e:
        return False, f"Server selection timeout: {str(e)}"
    except OperationFailure as e:
        return False, f"Operation failed: {str(e)}"
    except Exception as e:
        return False, f"Unknown error: {str(e)}"

def ensure_mongodb_running():
    """Ensure MongoDB is running before attempting connection"""
    try:
        # Check if MongoDB is accessible
        test_client = MongoClient(get_connection_string(), serverSelectionTimeoutMS=3000)
        test_client.admin.command('ping')
        test_client.close()
        return True
    except:
        print("🚀 MongoDB not running, attempting to start...")
        try:
            import subprocess
            import os
            
            # Create data directory
            data_path = "C:\\data\\db"
            if not os.path.exists(data_path):
                os.makedirs(data_path, exist_ok=True)
            
            # Start MongoDB in background
            subprocess.Popen([
                "mongod", 
                "--dbpath", data_path,
                "--logpath", os.path.join(data_path, "mongod.log")
            ], creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=True)
            
            # Wait for startup
            time.sleep(5)
            
            # Test connection again
            test_client = MongoClient(get_connection_string(), serverSelectionTimeoutMS=5000)
            test_client.admin.command('ping')
            test_client.close()
            print("✅ MongoDB started successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to start MongoDB: {str(e)}")
            return False

def establish_connection():
    """Establish MongoDB connection with enhanced retry mechanism and auto-start"""
    with connection_state['lock']:
        if connection_state['is_connected'] and connection_state['client'] is not None:
            return connection_state['client'], connection_state['db']
        
        print("🔄 Establishing MongoDB connection...")
        
        # Ensure MongoDB is running first
        if not ensure_mongodb_running():
            print("❌ Cannot establish connection - MongoDB unavailable")
            return None, None
        
        for attempt in range(connection_state['max_retries']):
            try:
                client = create_mongo_client()
                is_connected, message = test_connection(client)
                
                if is_connected:
                    db = client["smartstock"]
                    
                    # Update connection state
                    connection_state['client'] = client
                    connection_state['db'] = db
                    connection_state['is_connected'] = True
                    connection_state['last_check'] = datetime.datetime.now()
                    connection_state['retry_count'] = 0
                    
                    print("✅ MongoDB connected successfully with strong protection")
                    return client, db
                else:
                    print(f"❌ Connection attempt {attempt + 1} failed: {message}")
                    
            except Exception as e:
                print(f"❌ Connection attempt {attempt + 1} error: {str(e)}")
            
            if attempt < connection_state['max_retries'] - 1:
                wait_time = min((2 ** attempt) + 1, 10)  # Cap wait time at 10s
                print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        # All retries failed
        connection_state['retry_count'] = connection_state['max_retries']
        connection_state['is_connected'] = False
        print("❌ All connection attempts failed")
        return None, None

def get_robust_db():
    """Get database connection with automatic reconnection"""
    with connection_state['lock']:
        # Check if connection is still valid
        if (connection_state['is_connected'] and 
            connection_state['client'] is not None and
            connection_state['last_check'] and
            (datetime.datetime.now() - connection_state['last_check']).seconds < 30):
            
            try:
                # Quick connection test
                connection_state['client'].admin.command('ping')
                connection_state['last_check'] = datetime.datetime.now()
                return connection_state['db']
            except:
                print("⚠️ Connection lost, attempting reconnection...")
                connection_state['is_connected'] = False
        
        # Establish new connection if needed
        if not connection_state['is_connected']:
            client, db = establish_connection()
            return db
        
        return connection_state['db']

def check_robust_connection():
    """Check connection status with detailed information"""
    with connection_state['lock']:
        if connection_state['client'] is None:
            return False, "No client available"
        
        try:
            # Comprehensive connection test
            connection_state['client'].admin.command('ping')
            
            # Test database operations
            db = connection_state['db']
            if db is not None:
                db.list_collection_names()
            
            connection_state['last_check'] = datetime.datetime.now()
            return True, "Connection healthy"
        except Exception as e:
            connection_state['is_connected'] = False
            return False, f"Connection error: {str(e)}"

def close_connection():
    """Safely close MongoDB connection"""
    with connection_state['lock']:
        if connection_state['client'] is not None:
            try:
                connection_state['client'].close()
                print("✅ MongoDB connection closed safely")
            except Exception as e:
                print(f"⚠️ Error closing connection: {str(e)}")
            finally:
                connection_state['client'] = None
                connection_state['db'] = None
                connection_state['is_connected'] = False

# Initialize connection on startup with verification
print("🚀 SmartStock Application Starting...")
print("🔍 Verifying MongoDB connection before startup...")

# Multiple connection attempts with increasing timeouts
max_startup_attempts = 3
for attempt in range(max_startup_attempts):
    print(f"📡 Startup connection attempt {attempt + 1}/{max_startup_attempts}")
    
    client, db = establish_connection()
    if client is not None and db is not None:
        print("✅ MongoDB connection verified successfully!")
        break
    else:
        if attempt < max_startup_attempts - 1:
            print(f"⏳ Waiting 5 seconds before retry...")
            time.sleep(5)
        else:
            print("⚠️ Warning: Could not establish MongoDB connection after multiple attempts")
            print("🔄 Application will continue, but database features may be limited")

print("🎯 SmartStock initialization complete!")

# COLLECTIONS WITH ROBUST CONNECTION HANDLING
def get_collection(collection_name):
    """Get collection with automatic reconnection"""
    db = get_robust_db()
    if db is not None:
        return db[collection_name]
    return None

# Main collections
collection = get_collection("users")
products_collection = get_collection("products")
inventory_collection = get_collection("inventory")
sales_collection = get_collection("sales")
alerts_collection = get_collection("alerts")
reports_collection = get_collection("reports")
transactions_collection = get_collection("transactions")

# TEMP OTP STORAGE (NO DATABASE)
otp_storage = {}

# EMAIL CONFIG
EMAIL_ADDRESS = "smartstockinventory13@gmail.com"
EMAIL_PASSWORD = "mqba dccc kkls xnbs"

@app.route("/health")
def health_check():
    """Enhanced health check endpoint with detailed status"""
    try:
        is_connected, message = check_robust_connection()
        
        # Get connection statistics
        with connection_state['lock']:
            retry_count = connection_state['retry_count']
            last_check = connection_state['last_check']
            
        # Check database operations
        db_status = "operational"
        try:
            if products_collection is not None:
                products_collection.count_documents({})
        except:
            db_status = "limited"
        
        return jsonify({
            "status": "healthy" if is_connected else "unhealthy",
            "database": {
                "connected": is_connected,
                "status": db_status,
                "message": message,
                "last_check": last_check.isoformat() if last_check else None,
                "retry_count": retry_count
            },
            "collections": {
                "users": collection is not None,
                "products": products_collection is not None,
                "inventory": inventory_collection is not None,
                "sales": sales_collection is not None,
                "alerts": alerts_collection is not None,
                "reports": reports_collection is not None,
                "transactions": transactions_collection is not None
            },
            "timestamp": datetime.datetime.now().isoformat(),
            "uptime": "active" if is_connected else "disconnected"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

@app.route("/")
def home():
    try:
        return render_template("intro.html")
    except Exception as e:
        return f"Error loading intro.html: {str(e)}<br>Template folder: {app.template_folder}<br>Working dir: {os.getcwd()}"

@app.route("/test")
def test():
    return "Flask app is working! Current time: " + str(datetime.datetime.now())

@app.route("/intro")
def intro():
    return render_template("intro.html")

@app.route("/debug")
def debug():
    return jsonify({
        "status": "working",
        "templates": os.listdir("templates"),
        "intro_exists": os.path.exists("templates/intro.html")
    })

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

@app.route("/welcome")
def welcome():
    print(f"🔍 Welcome route accessed - Session data: {dict(session)}")
    
    # Check if user is logged in via session first
    if 'user_email' in session:
        print(f"✅ Found session data for: {session.get('user_email')}")
        return render_template("welcome.html")
    
    # Check for token in URL parameters (from login redirect)
    token = request.args.get('token')
    if not token:
        # Check for token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
    
    if token:
        try:
            print("🔍 Validating token...")
            data = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )
            print(f"✅ Token valid for user: {data.get('email')}")
            
            # Set session from token for future requests
            session['user_email'] = data.get('email', '')
            session['username'] = data.get('username', '')
            session['user_id'] = data.get('username', '')
            session.permanent = True
            
            print(f"✅ Session set for: {session.get('user_email')}")
            return render_template("welcome.html")
            
        except Exception as e:
            print(f"❌ Token validation failed: {e}")
    
    print("❌ No valid authentication found, redirecting to login")
    return redirect(url_for('login_page'))


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


# ---------------- ADDITIONAL PAGE ROUTES ----------------

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/user")
def user_page():
    return render_template("dashboard.html")

# DATABASE HELPER FUNCTION
def get_db():
    """Get database connection with error handling (legacy support)"""
    db = get_robust_db()
    if db is None:
        raise Exception("Database not connected")
    return db

# Connection monitoring decorator
def with_db_check(f):
    """Decorator to ensure database connection before API calls"""
    def wrapper(*args, **kwargs):
        try:
            # Ensure we have a valid connection
            db = get_robust_db()
            if db is None:
                return jsonify({
                    "error": "Database connection failed",
                    "message": "Unable to connect to database"
                }), 503
            
            return f(*args, **kwargs)
        except Exception as e:
            print(f"❌ Database operation failed: {str(e)}")
            return jsonify({
                "error": "Database operation failed",
                "message": str(e)
            }), 500
    return wrapper

# Enhanced collection operations with error handling
def safe_collection_operation(collection_name, operation):
    """Safely perform collection operation with error handling"""
    try:
        collection = get_collection(collection_name)
        if collection is None:
            raise Exception(f"Collection {collection_name} not available")
        return operation(collection)
    except Exception as e:
        print(f"❌ Collection operation failed: {str(e)}")
        raise e

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/employee-dashboard")
def employee_dashboard():
    return render_template("employee/employee_dashboard.html")

@app.route("/employee/products-view")
def employee_products_view():
    return render_template("employee/products_view.html")

@app.route("/employee/stock-update")
def employee_stock_update():
    return render_template("employee/stock_update.html")

@app.route("/employee/sales-entry")
def employee_sales_entry():
    return render_template("employee/sales_entry.html")

@app.route("/employee/alerts-view")
def employee_alerts_view():
    return render_template("employee/alerts_view.html")

@app.route("/employee/transaction-history")
def employee_transaction_history():
    return render_template("employee/transaction_history.html")

@app.route("/employee-profile")
def employee_profile():
    return render_template("employee/employee_profile.html")

@app.route("/products")
def products():
    return render_template("products.html")

@app.route("/inventory")
def inventory():
    return render_template("inventory.html")

@app.route("/sales")
def sales():
    return render_template("sales.html")

@app.route("/alerts")
def alerts():
    return render_template("alerts.html")

@app.route("/reports")
def reports():
    return render_template("reports.html")

@app.route("/transaction-history")
def transaction_history():
    return render_template("transaction_history.html")

@app.route("/smart-assistant")
def smart_assistant():
    return render_template("smart_assistant.html")

@app.route("/user-management")
def user_management():
    return render_template("user_management.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")


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
    device_info = data.get("deviceInfo", {})
    location = data.get("location", {})

    if not username or not password:
        return jsonify({"message": "Missing credentials"}), 400

    user = collection.find_one({
        "$or": [{"username": username}, {"email": username}]
    })

    if not user:
        return jsonify({"message": "Account does not exist"}), 401

    if not check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid password"}), 401

    # Update last login information
    login_session = {
        "timestamp": datetime.datetime.utcnow(),
        "deviceInfo": device_info,
        "location": location
    }
    
    collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "lastLogin": login_session,
                "loginHistory": user.get("loginHistory", [])[-9:] + [login_session]  # Keep last 10 logins
            }
        }
    )

    # Store user email in session for real-time alerts
    session['user_email'] = user.get("email", "")
    session['username'] = user.get("username", "")
    session['user_id'] = str(user["_id"])
    session.permanent = True  # Make session persist
    
    print(f"✅ User session created: {user.get('email')}")

    token = jwt.encode({
        "username": user["username"],
        "email": user["email"],  # Add email to token for alerts
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return jsonify({
        "message": "Login successful",
        "token": token,
        "role": user["role"],
        "user_name": user.get("username", ""),
        "user_email": user.get("email", "")
    })


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    """Logout user and clear session"""
    session.clear()
    return redirect(url_for('login_page'))

# ---------------- FORGOT PASSWORD ----------------

@app.route("/last-login/<username>", methods=["GET"])
def get_last_login(username):
    """Get last login information for a user"""
    try:
        user = collection.find_one({
            "$or": [{"username": username}, {"email": username}]
        })
        
        if not user:
            return jsonify({"message": "User not found"}), 404
            
        last_login = user.get("lastLogin")
        if not last_login:
            return jsonify({"lastLogin": None}), 200
            
        # Convert ObjectId to string for JSON serialization
        if "_id" in last_login:
            last_login["_id"] = str(last_login["_id"])
            
        return jsonify({"lastLogin": last_login}), 200
        
    except Exception as e:
        return jsonify({"message": "Error fetching last login"}), 500

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


# ---------------- THRESHOLD MANAGEMENT & ALERT SYSTEM ----------------

def get_category_thresholds():
    """Get default stock thresholds based on product categories"""
    return {
        "Electronics": 5,
        "Food": 20,
        "Beverages": 15,
        "Clothing": 10,
        "Furniture": 3,
        "Books": 25,
        "Toys": 15,
        "Sports": 8,
        "Beauty": 12,
        "Health": 10,
        "Office": 15,
        "Cleaning": 20,
        "general": 10
    }

def check_and_create_stock_alert(product, old_stock=None):
    """Check stock levels and create alerts if needed"""
    try:
        stock_qty = product.get('stock_quantity', 0)
        min_level = product.get('min_stock_level', 10)
        max_level = product.get('max_stock_level', 50)
        alert_enabled = product.get('alert_enabled', True)
        
        if not alert_enabled:
            return
        
        alert_type = None
        alert_message = ""
        alert_priority = "medium"
        
        # Check for different stock conditions
        if stock_qty == 0:
            alert_type = "out_of_stock"
            alert_message = f"CRITICAL: {product['name']} is completely out of stock!"
            alert_priority = "critical"
        elif stock_qty <= min_level:
            alert_type = "low_stock"
            alert_message = f"WARNING: {product['name']} stock is low ({stock_qty} units, threshold: {min_level})"
            alert_priority = "high"
        elif stock_qty >= max_level:
            alert_type = "overstock"
            alert_message = f"INFO: {product['name']} stock is high ({stock_qty} units, max: {max_level})"
            alert_priority = "low"
        elif old_stock is not None and stock_qty < old_stock and stock_qty <= min_level * 1.2:
            alert_type = "stock_decrease"
            alert_message = f"CAUTION: {product['name']} stock decreased to {stock_qty} units"
            alert_priority = "medium"
        
        # Create alert if condition detected
        if alert_type:
            create_stock_alert(product, alert_type, alert_message, alert_priority)
            
    except Exception as e:
        print(f"Error checking stock alert: {str(e)}")

def create_stock_alert(product, alert_type, message, priority):
    """Create a stock alert in the database"""
    try:
        # Check if alert already exists for this product and alert type
        existing_alert = alerts_collection.find_one({
            "product_id": str(product['_id']),
            "alert_type": alert_type,
            "status": "active"
        })
        
        if existing_alert:
            # Update existing alert with new stock quantity and message
            alerts_collection.update_one(
                {"_id": existing_alert["_id"]},
                {
                    "$set": {
                        "message": message,
                        "stock_quantity": product.get('stock_quantity', 0),
                        "min_stock_level": product.get('min_stock_level', 10),
                        "created_at": datetime.datetime.now()  # Update timestamp
                    }
                }
            )
            print(f"Updated existing alert for product {product['name']} ({alert_type})")
            return
        
        # Create new alert if none exists
        alert = {
            "product_id": str(product['_id']),
            "product_name": product['name'],
            "product_sku": product.get('sku', ''),
            "alert_type": alert_type,
            "message": message,
            "priority": priority,
            "status": "active",
            "stock_quantity": product.get('stock_quantity', 0),
            "min_stock_level": product.get('min_stock_level', 10),
            "created_at": datetime.datetime.now(),
            "acknowledged_by": None,
            "acknowledged_at": None
        }
        
        alerts_collection.insert_one(alert)
        
        # Send notifications if configured
        send_stock_notification(product, alert_type, message, priority)
        
    except Exception as e:
        print(f"Error creating stock alert: {str(e)}")

def send_stock_notification(product, alert_type, message, priority):
    """Send email notifications to currently logged-in user from active session"""
    try:
        # Get current logged-in user's email from active session (REAL-TIME)
        recipient_email = None
        
        try:
            from flask import request, session
            print("🔍 Checking for active user session...")
            
            # Method 1: Get from active session (PRIORITY - Real-time)
            if 'user_email' in session and session['user_email']:
                recipient_email = session['user_email']
                print(f"✅ Found logged-in user from ACTIVE SESSION: {recipient_email}")
            
            # Method 2: Get from JWT token (fallback)
            if not recipient_email:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    try:
                        token = auth_header.split(' ')[1]
                        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
                        recipient_email = decoded.get('email')
                        print(f"✅ Found logged-in user from JWT TOKEN: {recipient_email}")
                    except Exception as e:
                        print(f"⚠️ Could not decode token: {str(e)}")
            
            # Method 3: Get from session username (another fallback)
            if not recipient_email and 'username' in session:
                user = collection.find_one({"username": session['username']})
                if user:
                    recipient_email = user.get('email')
                    print(f"✅ Found logged-in user from SESSION USERNAME: {recipient_email}")
                    
        except Exception as e:
            print(f"⚠️ Error getting logged-in user: {str(e)}")
        
        # If no logged-in user found, do not send email
        if not recipient_email:
            print("❌ No logged-in user found in active session - NO EMAIL SENT")
            print("🔒 Alert restricted: Only active logged-in users receive notifications")
            print("🔍 DEBUG: This means you need to login first!")
            return
        
        # Validate email format
        if '@' not in recipient_email or '.' not in recipient_email:
            print(f"❌ Invalid email format: {recipient_email}")
            return
        
        print(f"📧 Sending alert to ACTIVE SESSION USER: {recipient_email}")
        print(f"🔒 Real-time notification: Only this user receives alert")
        
        # Prepare email content with professional headers
        subject = f"Stock Alert - {alert_type.replace('_', ' ').title()}: {product['name']}"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="background-color: #f8f9fa; padding: 20px; border-left: 4px solid #dc3545; margin: 20px 0; border-radius: 4px;">
                <h2 style="color: #dc3545; margin-top: 0;">📦 SmartStock Inventory Alert</h2>
                <p><strong>Product:</strong> {product['name']}</p>
                <p><strong>SKU:</strong> {product.get('sku', 'N/A')}</p>
                <p><strong>Category:</strong> {product.get('category', 'N/A')}</p>
                <p><strong>Current Stock:</strong> <span style="color: #dc3545; font-weight: bold;">{product.get('stock_quantity', 0)} units</span></p>
                <p><strong>Minimum Threshold:</strong> {product.get('min_stock_level', 10)} units</p>
                <p><strong>Alert Type:</strong> {alert_type.replace('_', ' ').title()}</p>
                <p><strong>Priority:</strong> {priority.upper()}</p>
                <p><strong>Alert Message:</strong> {message}</p>
                <p><strong>Time:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                <p style="margin-bottom: 0;"><em>Please review your inventory levels and consider restocking soon.</em></p>
                <p style="margin-bottom: 0; font-size: 12px; color: #6c757d;">This is an automated message from SmartStock Inventory Management System</p>
            </div>
        </body>
        </html>
        """
        
        # Send email to single authenticated user only with professional headers
        try:
            msg = MIMEText(email_body, 'html')
            msg["Subject"] = subject
            msg["From"] = f"SmartStock System <{EMAIL_ADDRESS}>"
            msg["To"] = recipient_email
            msg["Reply-To"] = EMAIL_ADDRESS
            msg["Return-Path"] = EMAIL_ADDRESS
            msg["X-Mailer"] = "SmartStock Alert System v1.0"
            msg["X-Priority"] = "3"  # Normal priority
            msg["Importance"] = "normal"
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
            server.quit()
            
            print(f"✅ Alert email sent to logged-in user: {recipient_email}")
            print(f"🔒 Security: Only active user received this notification")
            
        except Exception as e:
            print(f"❌ Failed to send email to {recipient_email}: {str(e)}")
                
    except Exception as e:
        print(f"Error sending stock notification: {str(e)}")

# ---------------- THRESHOLD MANAGEMENT API ENDPOINTS ----------------

@app.route("/api/thresholds/categories", methods=["GET"])
def get_category_thresholds_api():
    """Get default thresholds for all categories"""
    try:
        return jsonify({"category_thresholds": get_category_thresholds()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/thresholds/update-batch", methods=["POST"])
def update_batch_thresholds():
    """Update thresholds for multiple products at once"""
    try:
        data = request.get_json()
        product_updates = data.get("products", [])
        
        updated_count = 0
        for update in product_updates:
            product_id = update.get("product_id")
            min_level = update.get("min_stock_level")
            threshold_type = update.get("threshold_type", "custom")
            
            if product_id and min_level is not None:
                products_collection.update_one(
                    {"_id": ObjectId(product_id)},
                    {
                        "$set": {
                            "min_stock_level": int(min_level),
                            "threshold_type": threshold_type,
                            "updated_at": datetime.datetime.now()
                        }
                    }
                )
                updated_count += 1
        
        return jsonify({
            "message": f"Updated thresholds for {updated_count} products",
            "updated_count": updated_count
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts", methods=["GET", "POST"])
def manage_alerts():
    if request.method == "GET":
        try:
            # Get query parameters for filtering
            status = request.args.get("status", "active")
            priority = request.args.get("priority", "")
            alert_type = request.args.get("type", "")
            
            # Build filter
            filter_query = {}
            if status and status != "all":
                filter_query["status"] = status
            if priority and priority != "all":
                filter_query["priority"] = priority
            if alert_type and alert_type != "all":
                filter_query["alert_type"] = alert_type
            
            alerts = list(alerts_collection.find(filter_query).sort("created_at", -1))
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
                # Convert datetime to ISO string for proper JSON serialization
                if 'created_at' in alert and alert['created_at']:
                    if isinstance(alert['created_at'], datetime.datetime):
                        alert['created_at'] = alert['created_at'].isoformat()
                    else:
                        alert['created_at'] = str(alert['created_at'])
                
            return jsonify({"alerts": alerts})
        except Exception as e:
            print(f"Error loading alerts: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            alert = {
                "product_id": data.get("product_id"),
                "product_name": data.get("product_name"),
                "alert_type": data.get("alert_type"),
                "message": data.get("message"),
                "priority": data.get("priority", "medium"),
                "status": data.get("status", "active"),
                "created_at": datetime.datetime.now()
            }
            
            result = alerts_collection.insert_one(alert)
            alert['_id'] = str(result.inserted_id)
            
            return jsonify({"message": "Alert created successfully", "alert": alert}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/notifications", methods=["GET"])
def get_notifications():

    try:

        alerts_collection = get_collection("alerts")

        recent_alerts = list(
            alerts_collection.find(
                {"status": {"$ne": "resolved"}}
            ).sort("created_at", -1).limit(5)
        )

        notifications = []
        unread_count = 0

        for alert in recent_alerts:

            notification = {
                "id": str(alert["_id"]),
                "title": alert.get("alert_type", "Alert"),
                "message": alert.get("message", ""),
                "priority": alert.get("priority", "medium"),
                "read": alert.get("status") == "acknowledged"
            }

            notifications.append(notification)

            if alert.get("status") != "acknowledged":
                unread_count += 1

        return jsonify({
            "notifications": notifications,
            "unread_count": unread_count
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def get_time_ago(created_at):
    """Calculate time ago string"""
    if not created_at:
        return "Just now"
    
    now = datetime.datetime.now()
    if isinstance(created_at, str):
        created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    diff = now - created_at
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"

@app.route("/api/notifications/<notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        alerts_collection = db["alerts"]
        result = alerts_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"status": "acknowledged"}}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Notification marked as read"}), 200
        else:
            return jsonify({"error": "Notification not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/notifications/clear", methods=["POST"])
def clear_all_notifications():
    """Clear all notifications"""
    try:
        alerts_collection = db["alerts"]
        result = alerts_collection.update_many(
            {"status": {"$ne": "resolved"}},
            {"$set": {"status": "acknowledged"}}
        )
        
        return jsonify({
            "message": f"Cleared {result.modified_count} notifications"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/cleanup-duplicates", methods=["POST"])
def cleanup_duplicate_alerts():
    """Remove duplicate alerts for the same product and alert type"""
    try:
        # Find all active alerts grouped by product_id and alert_type
        pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": {"product_id": "$product_id", "alert_type": "$alert_type"},
                "alerts": {"$push": "$_id"},
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = list(alerts_collection.aggregate(pipeline))
        
        removed_count = 0
        for duplicate_group in duplicates:
            # Keep the newest alert (highest _id in ObjectId comparison)
            alerts_to_remove = sorted(duplicate_group["alerts"])[:-1]  # Remove all except the last one
            
            result = alerts_collection.delete_many({"_id": {"$in": alerts_to_remove}})
            removed_count += result.deleted_count
        
        return jsonify({
            "message": f"Cleaned up {removed_count} duplicate alerts",
            "duplicate_groups": len(duplicates)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/clear", methods=["POST"])
def clear_all_alerts():
    """Delete all alerts from database"""
    try:
        alerts_collection = db["alerts"]
        result = alerts_collection.delete_many({})
        
        return jsonify({
            "message": f"Deleted {result.deleted_count} alerts from database",
            "deleted_count": result.deleted_count
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        alerts_collection.update_one(
            {"_id": ObjectId(alert_id)},
            {
                "$set": {
                    "status": "acknowledged",
                    "acknowledged_by": "admin",  # Should get from token in production
                    "acknowledged_at": datetime.datetime.now()
                }
            }
        )
        
        return jsonify({"message": "Alert acknowledged successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- DASHBOARD API ENDPOINTS ----------------

@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    try:
        total_products = products_collection.count_documents({})
        
        # Calculate total stock and threshold-based stats
        products = list(products_collection.find({}, {
            'stock_quantity': 1, 
            'min_stock_level': 1, 
            'category': 1
        }))
        
        total_stock = sum(product.get('stock_quantity', 0) for product in products)
        
        # Calculate low stock items based on individual thresholds
        low_stock_items = [p for p in products if p.get('stock_quantity', 0) <= p.get('min_stock_level', 10)]
        out_of_stock_items = [p for p in products if p.get('stock_quantity', 0) == 0]
        
        # Get active alerts
        active_alerts = alerts_collection.count_documents({"status": "active"})
        critical_alerts = alerts_collection.count_documents({"status": "active", "priority": "critical"})
        
        # Sales stats
        today_sales = sales_collection.count_documents({"date": datetime.datetime.now().strftime("%Y-%m-%d")})
        total_transactions = sales_collection.count_documents({})
        
        # Category breakdown
        category_stats = {}
        for product in products:
            category = product.get('category', 'general')
            if category not in category_stats:
                category_stats[category] = {'count': 0, 'stock': 0, 'low_stock': 0}
            category_stats[category]['count'] += 1
            category_stats[category]['stock'] += product.get('stock_quantity', 0)
            if product.get('stock_quantity', 0) <= product.get('min_stock_level', 10):
                category_stats[category]['low_stock'] += 1

        return jsonify({
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_items": len(low_stock_items),
            "out_of_stock_items": len(out_of_stock_items),
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "today_sales": today_sales,
            "total_transactions": total_transactions,
            "category_stats": category_stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/products", methods=["GET", "POST"])
def manage_products():
    if request.method == "GET":
        try:
            products = list(products_collection.find({}))
            for product in products:
                product['_id'] = str(product['_id'])
                # Add stock status based on threshold
                stock_qty = product.get('stock_quantity', 0)
                min_level = product.get('min_stock_level', 10)
                
                if stock_qty == 0:
                    product['stock_status'] = 'out_of_stock'
                    product['stock_status_color'] = 'danger'
                elif stock_qty <= min_level:
                    product['stock_status'] = 'low_stock'
                    product['stock_status_color'] = 'warning'
                else:
                    product['stock_status'] = 'in_stock'
                    product['stock_status_color'] = 'success'
                    
            return jsonify({"products": products})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            
            # Enhanced threshold management
            category = data.get("category", "general")
            category_thresholds = get_category_thresholds()
            default_threshold = category_thresholds.get(category, 10)
            
            product = {
                "name": data.get("name"),
                "sku": data.get("sku"),
                "category": category,
                "supplier": data.get("supplier"),
                "price": float(data.get("price")),
                "stock_quantity": int(data.get("stock_quantity")),
                "min_stock_level": int(data.get("min_stock_level", default_threshold)),
                "threshold_type": data.get("threshold_type", "custom"),  # custom, category_based, auto
                "reorder_point": int(data.get("reorder_point", data.get("min_stock_level", default_threshold) * 1.5)),
                "max_stock_level": int(data.get("max_stock_level", data.get("min_stock_level", default_threshold) * 5)),
                "alert_enabled": data.get("alert_enabled", True),
                "alert_recipients": data.get("alert_recipients", []),
                "created_at": datetime.datetime.now(),
                "updated_at": datetime.datetime.now()
            }
            
            result = products_collection.insert_one(product)
            product['_id'] = str(result.inserted_id)
            
            # Check if stock is below threshold and create alert
            check_and_create_stock_alert(product)
            
            return jsonify({"message": "Product added successfully", "product": product}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/products/<product_id>", methods=["PUT", "DELETE"])
def manage_product(product_id):
    if request.method == "PUT":
        try:
            data = request.get_json()
            
            # Get current product to check stock changes
            current_product = products_collection.find_one({"_id": ObjectId(product_id)})
            if not current_product:
                return jsonify({"message": "Product not found"}), 404
            
            old_stock = current_product.get('stock_quantity', 0)
            new_stock = int(data.get("stock_quantity", old_stock))
            
            update_data = {
                "name": data.get("name", current_product.get("name")),
                "sku": data.get("sku", current_product.get("sku")),
                "category": data.get("category", current_product.get("category")),
                "supplier": data.get("supplier", current_product.get("supplier")),
                "price": float(data.get("price", current_product.get("price", 0))),
                "stock_quantity": new_stock,
                "min_stock_level": int(data.get("min_stock_level", current_product.get('min_stock_level', 10))),
                "threshold_type": data.get("threshold_type", current_product.get('threshold_type', 'custom')),
                "reorder_point": int(data.get("reorder_point", current_product.get('reorder_point', 15))),
                "max_stock_level": int(data.get("max_stock_level", current_product.get('max_stock_level', 50))),
                "alert_enabled": data.get("alert_enabled", current_product.get('alert_enabled', True)),
                "alert_recipients": data.get("alert_recipients", current_product.get('alert_recipients', [])),
                "updated_at": datetime.datetime.now()
            }
            
            products_collection.update_one({"_id": ObjectId(product_id)}, {"$set": update_data})
            
            # Get updated product for alert checking
            updated_product = products_collection.find_one({"_id": ObjectId(product_id)})
            updated_product['_id'] = str(updated_product['_id'])
            
            # Check for stock changes and create alerts
            if old_stock != new_stock:
                check_and_create_stock_alert(updated_product, old_stock)
            
            return jsonify({"message": "Product updated successfully", "product": updated_product})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "DELETE":
        try:
            products_collection.delete_one({"_id": ObjectId(product_id)})
            return jsonify({"message": "Product deleted successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/sales", methods=["GET", "POST"])
def manage_sales():
    if request.method == "GET":
        try:
            sales = list(sales_collection.find({}))
            for sale in sales:
                sale['_id'] = str(sale['_id'])
            return jsonify({"sales": sales})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            sale = {
                "product_id": data.get("product_id"),
                "product_name": data.get("product_name"),
                "quantity": int(data.get("quantity")),
                "unit_price": float(data.get("unit_price")),
                "total_amount": float(data.get("total_amount")),
                "payment_method": data.get("payment_method"),
                "customer_name": data.get("customer_name"),
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "created_at": datetime.datetime.now()
            }
            
            # Update product stock
            products_collection.update_one(
                {"_id": ObjectId(data.get("product_id"))},
                {"$inc": {"stock_quantity": -int(data.get("quantity"))}}
            )
            
            result = sales_collection.insert_one(sale)
            sale['_id'] = str(result.inserted_id)
            return jsonify({"message": "Sale recorded successfully", "sale": sale}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/inventory/update", methods=["POST"])
def update_inventory():
    try:
        data = request.get_json()
        product_id = data.get("product_id")
        operation = data.get("operation")  # "stock_in" or "stock_out"
        quantity = int(data.get("quantity"))
        reason = data.get("reason", "Manual update")
        
        # Get product details for audit log
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Record transaction before update
        transaction = {
            "product_id": product_id,
            "product_name": product.get("name", "Unknown"),
            "product_sku": product.get("sku", "Unknown"),
            "transaction_type": operation,
            "quantity": quantity,
            "previous_stock": product.get("stock_quantity", 0),
            "reason": reason,
            "timestamp": datetime.datetime.now(),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        }
        
        if operation == "stock_in":
            products_collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$inc": {"stock_quantity": quantity}}
            )
            transaction["new_stock"] = product.get("stock_quantity", 0) + quantity
        elif operation == "stock_out":
            # Check if enough stock is available
            if product.get("stock_quantity", 0) < quantity:
                return jsonify({"error": "Insufficient stock available"}), 400
            products_collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$inc": {"stock_quantity": -quantity}}
            )
            transaction["new_stock"] = product.get("stock_quantity", 0) - quantity
        else:
            return jsonify({"error": "Invalid operation"}), 400
        
        # Save transaction to database
        transactions_collection.insert_one(transaction)
        
        return jsonify({"message": f"Stock {operation.replace('_', ' ')} successful", "transaction": transaction})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    try:
        # Get query parameters for filtering
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        product_id = request.args.get("product_id")
        transaction_type = request.args.get("transaction_type")
        
        # Build query
        query = {}
        if start_date and end_date:
            query["date"] = {"$gte": start_date, "$lte": end_date}
        if product_id:
            query["product_id"] = product_id
        if transaction_type:
            query["transaction_type"] = transaction_type
        
        transactions = list(transactions_collection.find(query).sort("timestamp", -1))
        for transaction in transactions:
            transaction['_id'] = str(transaction['_id'])
        
        return jsonify({"transactions": transactions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def check_all_products_for_low_stock():
    """Check all products for low stock and send alerts to user emails"""
    try:
        # Get all users to send alerts to
        users = list(collection.find({"email": {"$exists": True}}, {"email": 1, "username": 1}))
        user_emails = [user['email'] for user in users if 'email' in user]
        
        # Get all products
        products = list(products_collection.find({}))
        
        alerts_created = 0
        
        for product in products:
            stock_qty = product.get('stock_quantity', 0)
            min_level = product.get('min_stock_level', 10)
            alert_enabled = product.get('alert_enabled', True)
            
            # Check if product needs alert
            if alert_enabled and stock_qty <= min_level:
                # Check if alert already exists for this product and alert type
                alert_type = "out_of_stock" if stock_qty == 0 else "low_stock"
                existing_alert = alerts_collection.find_one({
                    "product_id": str(product['_id']),
                    "alert_type": alert_type,
                    "status": "active"
                })
                
                if not existing_alert:
                    # Create alert for this product
                    priority = "critical" if stock_qty == 0 else "high"
                    
                    alert = {
                        "product_id": str(product['_id']),
                        "product_name": product.get('name', 'Unknown'),
                        "product_sku": product.get('sku', ''),
                        "alert_type": alert_type,
                        "message": f"{'CRITICAL' if stock_qty == 0 else 'WARNING'}: {product.get('name', 'Unknown')} stock is {alert_type.replace('_', ' ')} ({stock_qty} units, threshold: {min_level})",
                        "priority": priority,
                        "status": "active",
                        "stock_quantity": stock_qty,
                        "min_stock_level": min_level,
                        "created_at": datetime.datetime.now(),
                        "acknowledged_by": None,
                        "acknowledged_at": None
                    }
                    
                    alerts_collection.insert_one(alert)
                    alerts_created += 1
                    
                    # Send email to all users
                    send_low_stock_email_to_users(product, alert_type, priority, user_emails)
        
        if alerts_created > 0:
            print(f"✅ Created {alerts_created} low stock alerts and sent emails to {len(user_emails)} users")
        
        return alerts_created
        
    except Exception as e:
        print(f"❌ Error checking products for low stock: {str(e)}")
        return 0

@app.route("/api/generate-alerts", methods=["POST"])
def generate_alerts():
    """Manually trigger alert generation for all products"""
    try:
        alerts_created = check_all_products_for_low_stock()
        return jsonify({
            "message": f"Alert generation completed successfully",
            "alerts_created": alerts_created
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def send_low_stock_email_to_users(product, alert_type, priority, user_emails):
    """Send low stock alert email to all users"""
    try:
        stock_qty = product.get('stock_quantity', 0)
        min_level = product.get('min_stock_level', 10)
        
        # Prepare email content
        subject = f"🚨 SmartStock Alert - {alert_type.replace('_', ' ').title()}: {product.get('name', 'Unknown')}"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white;">
                <h2 style="margin: 0; text-align: center;">🚨 SmartStock Inventory Alert</h2>
                <p style="margin: 10px 0; text-align: center; font-size: 18px;">
                    {priority.upper()} PRIORITY ALERT
                </p>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #dc3545; margin-top: 0;">Product Details:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Product Name:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{product.get('name', 'Unknown')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">SKU:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{product.get('sku', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Category:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{product.get('category', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Current Stock:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #dc3545; font-weight: bold;">{stock_qty} units</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Minimum Threshold:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{min_level} units</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <h4 style="color: #856404; margin-top: 0;">⚠️ Action Required:</h4>
                <p style="margin: 5px 0;">
                    {'Product is completely OUT OF STOCK! Immediate action required!' if stock_qty == 0 else f'Product stock is running low. Please reorder soon to avoid stockout.'}
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://127.0.0.1:5000/products" style="background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    📦 Manage Inventory
                </a>
            </div>
            
            <div style="background: #e9ecef; padding: 15px; border-radius: 10px; text-align: center; font-size: 12px; color: #6c757d;">
                <p style="margin: 0;">
                    This is an automated alert from SmartStock Inventory Management System<br>
                    Alert Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    📧 Sent to {len(user_emails)} registered users
                </p>
            </div>
        </body>
        </html>
        """
        
        # Send email to all users
        for recipient in user_emails:
            try:
                msg = MIMEText(email_body, 'html')
                msg["Subject"] = subject
                msg["From"] = EMAIL_ADDRESS
                msg["To"] = recipient
                
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
                server.quit()
                
                print(f"✅ Low stock alert email sent to {recipient}")
                
            except Exception as e:
                print(f"❌ Failed to send email to {recipient}: {str(e)}")
                
    except Exception as e:
        print(f"❌ Error sending low stock email: {str(e)}")

# Add automatic monitoring route
# Add test email route
@app.route("/api/test-user-email", methods=["POST"])
def test_user_email():
    """Test sending email to registered users"""
    try:
        # Get all users
        users = list(collection.find({"email": {"$exists": True}}, {"email": 1, "username": 1}))
        user_emails = [user['email'] for user in users if 'email' in user]
        
        if not user_emails:
            return jsonify({"message": "No users with email found"}), 404
        
        # Send test email
        subject = "🧪 SmartStock System Test - Email Notifications Working"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 20px; border-radius: 10px; color: white; text-align: center;">
                <h2 style="margin: 0;">✅ SmartStock Email System Test</h2>
                <p style="margin: 10px 0; font-size: 18px;">Your email notifications are working perfectly!</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #28a745; margin-top: 0;">🎉 Test Successful!</h3>
                <p style="margin: 10px 0;">
                    This email confirms that your SmartStock inventory alert system is working correctly.
                    When any product falls below its minimum stock level, you will receive automatic email alerts just like this one.
                </p>
                
                <div style="background: #d4edda; padding: 15px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #28a745;">
                    <h4 style="color: #155724; margin-top: 0;">✅ What's Working:</h4>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>✅ User email registration</li>
                        <li>✅ Product threshold monitoring</li>
                        <li>✅ Automatic alert creation</li>
                        <li>✅ Email notification delivery</li>
                        <li>✅ Professional HTML formatting</li>
                    </ul>
                </div>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://127.0.0.1:5000/products" style="background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    📦 Go to SmartStock
                </a>
            </div>
            
            <div style="background: #e9ecef; padding: 15px; border-radius: 10px; text-align: center; font-size: 12px; color: #6c757d;">
                <p style="margin: 0;">
                    This is a test email from SmartStock Inventory Management System<br>
                    Test Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    📧 Sent to {len(user_emails)} registered user(s)
                </p>
            </div>
        </body>
        </html>
        """
        
        # Send email to all users
        for recipient in user_emails:
            try:
                msg = MIMEText(email_body, 'html')
                msg["Subject"] = subject
                msg["From"] = EMAIL_ADDRESS
                msg["To"] = recipient
                
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
                server.quit()
                
                print(f"✅ Test email sent to {recipient}")
                
            except Exception as e:
                print(f"❌ Failed to send test email to {recipient}: {str(e)}")
        
        return jsonify({
            "message": f"Test email sent to {len(user_emails)} users",
            "users_count": len(user_emails),
            "emails_sent": user_emails
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/check-low-stock", methods=["POST"])
def trigger_low_stock_check():
    """Manual trigger for low stock checking"""
    try:
        alerts_created = check_all_products_for_low_stock()
        return jsonify({
            "message": f"Low stock check completed. Created {alerts_created} alerts.",
            "alerts_created": alerts_created
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/clear-test-users", methods=["POST"])
def clear_test_users():
    """Clear test/demo users only"""
    try:
        # Clear test users (those with test emails)
        test_emails = ["testuser@example.com"]
        result = collection.delete_many({"email": {"$in": test_emails}})
        
        return jsonify({
            "message": f"Removed {result.deleted_count} test users",
            "users_removed": result.deleted_count
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    """Resolve a specific alert"""
    try:
        # Convert string ID to ObjectId if needed
        from bson import ObjectId
        try:
            object_id = ObjectId(alert_id)
            query = {"_id": object_id}
        except:
            query = {"_id": alert_id}
        
        # Update alert status to resolved
        result = alerts_collection.update_one(
            query,
            {
                "$set": {
                    "status": "resolved",
                    "acknowledged_at": datetime.datetime.utcnow(),
                    "acknowledged_by": "user"  # You can get actual user from session
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({
                "message": "Alert resolved successfully",
                "alert_id": alert_id
            }), 200
        else:
            return jsonify({"error": "Alert not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<alert_id>/dismiss", methods=["POST"])
def dismiss_alert(alert_id):
    """Dismiss a specific alert"""
    try:
        # Convert string ID to ObjectId if needed
        from bson import ObjectId
        try:
            object_id = ObjectId(alert_id)
            query = {"_id": object_id}
        except:
            query = {"_id": alert_id}
        
        # Update alert status to dismissed
        result = alerts_collection.update_one(
            query,
            {
                "$set": {
                    "status": "dismissed",
                    "acknowledged_at": datetime.datetime.utcnow(),
                    "acknowledged_by": "user"  # You can get actual user from session
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({
                "message": "Alert dismissed successfully",
                "alert_id": alert_id
            }), 200
        else:
            return jsonify({"error": "Alert not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<alert_id>/delete", methods=["DELETE"])
def delete_alert(alert_id):
    """Delete a specific alert"""
    try:
        # Convert string ID to ObjectId if needed
        from bson import ObjectId
        try:
            object_id = ObjectId(alert_id)
            query = {"_id": object_id}
        except:
            query = {"_id": alert_id}
        
        # Delete the alert
        result = alerts_collection.delete_one(query)
        
        if result.deleted_count > 0:
            return jsonify({
                "message": "Alert deleted successfully",
                "alert_id": alert_id
            }), 200
        else:
            return jsonify({"error": "Alert not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/statistics", methods=["GET"])
def get_alert_statistics():
    """Get alert statistics"""
    try:
        stats = {}
        
        # Count by status
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = list(alerts_collection.aggregate(status_pipeline))
        stats["by_status"] = {item["_id"]: item["count"] for item in status_counts}
        
        # Count by priority
        priority_pipeline = [
            {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
        ]
        priority_counts = list(alerts_collection.aggregate(priority_pipeline))
        stats["by_priority"] = {item["_id"]: item["count"] for item in priority_counts}
        
        # Count by alert type
        type_pipeline = [
            {"$group": {"_id": "$alert_type", "count": {"$sum": 1}}}
        ]
        type_counts = list(alerts_collection.aggregate(type_pipeline))
        stats["by_type"] = {item["_id"]: item["count"] for item in type_counts}
        
        # Total counts
        stats["total"] = alerts_collection.count_documents({})
        stats["active"] = alerts_collection.count_documents({"status": "active"})
        stats["resolved"] = alerts_collection.count_documents({"status": "resolved"})
        stats["critical"] = alerts_collection.count_documents({"alert_type": "critical"})
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/clear-demo-data", methods=["POST"])
def clear_demo_data():
    """Clear all demo/test data from collections"""
    try:
        # Clear all products
        products_collection.delete_many({})
        
        # Clear all alerts
        alerts_collection.delete_many({})
        
        # Clear all sales
        sales_collection.delete_many({})
        
        # Clear all transactions
        transactions_collection.delete_many({})
        
        # Clear all reports
        reports_collection.delete_many({})
        
        return jsonify({
            "message": "All demo data cleared successfully",
            "cleared_collections": ["products", "alerts", "sales", "transactions", "reports"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cleanup-duplicates", methods=["POST"])
def cleanup_all_duplicates():
    """Remove duplicate data across all collections"""
    try:
        cleanup_results = {}
        
        # Cleanup duplicate products
        product_pipeline = [
            {"$group": {
                "_id": {"name": "$name", "category": "$category"},
                "count": {"$sum": 1},
                "latest": {"$max": "$_id"}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicate_products = list(products_collection.aggregate(product_pipeline))
        
        products_removed = 0
        for duplicate in duplicate_products:
            # Remove all except the latest
            result = products_collection.delete_many({
                "name": duplicate["_id"]["name"],
                "category": duplicate["_id"]["category"],
                "_id": {"$ne": duplicate["latest"]}
            })
            products_removed += result.deleted_count
        
        cleanup_results["products"] = products_removed
        
        # Cleanup duplicate alerts (already exists but we'll integrate here)
        alert_pipeline = [
            {"$group": {
                "_id": {"product_id": "$product_id", "alert_type": "$alert_type"},
                "count": {"$sum": 1},
                "latest": {"$max": "$created_at"}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicate_alerts = list(alerts_collection.aggregate(alert_pipeline))
        
        alerts_removed = 0
        for duplicate in duplicate_alerts:
            # Remove all except the latest
            result = alerts_collection.delete_many({
                "product_id": duplicate["_id"]["product_id"],
                "alert_type": duplicate["_id"]["alert_type"],
                "created_at": {"$ne": duplicate["latest"]}
            })
            alerts_removed += result.deleted_count
        
        cleanup_results["alerts"] = alerts_removed
        
        # Cleanup duplicate sales
        sales_pipeline = [
            {"$group": {
                "_id": {"product_id": "$product_id", "timestamp": "$timestamp"},
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicate_sales = list(sales_collection.aggregate(sales_pipeline))
        
        sales_removed = 0
        for duplicate in duplicate_sales:
            # Keep only one record per product per timestamp
            result = sales_collection.delete_many({
                "product_id": duplicate["_id"]["product_id"],
                "timestamp": duplicate["_id"]["timestamp"]
            })
            sales_removed += result.deleted_count - 1  # Keep one, remove rest
        
        cleanup_results["sales"] = sales_removed
        
        # Cleanup duplicate transactions
        transaction_pipeline = [
            {"$group": {
                "_id": {"transaction_id": "$transaction_id"},
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicate_transactions = list(transactions_collection.aggregate(transaction_pipeline))
        
        transactions_removed = 0
        for duplicate in duplicate_transactions:
            # Keep only one record per transaction_id
            result = transactions_collection.delete_many({
                "transaction_id": duplicate["_id"]["transaction_id"]
            })
            transactions_removed += result.deleted_count - 1  # Keep one, remove rest
        
        cleanup_results["transactions"] = transactions_removed
        
        total_removed = sum(cleanup_results.values())
        
        return jsonify({
            "message": "Duplicate data cleanup completed successfully",
            "cleanup_results": cleanup_results,
            "total_duplicates_removed": total_removed
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/data-integrity", methods=["GET"])
def check_data_integrity():
    """Check data integrity and report issues"""
    try:
        integrity_report = {}
        
        # Check products
        total_products = products_collection.count_documents({})
        products_with_invalid_stock = products_collection.count_documents({
            "$or": [
                {"stock_quantity": {"$lt": 0}},
                {"stock_quantity": {"$type": "null"}},
                {"price": {"$lt": 0}},
                {"price": {"$type": "null"}}
            ]
        })
        
        integrity_report["products"] = {
            "total": total_products,
            "invalid_records": products_with_invalid_stock,
            "valid": total_products - products_with_invalid_stock
        }
        
        # Check alerts
        total_alerts = alerts_collection.count_documents({})
        alerts_with_invalid_data = alerts_collection.count_documents({
            "$or": [
                {"product_id": {"$type": "null"}},
                {"alert_type": {"$type": "null"}},
                {"status": {"$type": "null"}}
            ]
        })
        
        integrity_report["alerts"] = {
            "total": total_alerts,
            "invalid_records": alerts_with_invalid_data,
            "valid": total_alerts - alerts_with_invalid_data
        }
        
        # Check sales
        total_sales = sales_collection.count_documents({})
        sales_with_invalid_data = sales_collection.count_documents({
            "$or": [
                {"product_id": {"$type": "null"}},
                {"quantity": {"$lt": 0}},
                {"total_amount": {"$lt": 0}}
            ]
        })
        
        integrity_report["sales"] = {
            "total": total_sales,
            "invalid_records": sales_with_invalid_data,
            "valid": total_sales - sales_with_invalid_data
        }
        
        # Check transactions
        total_transactions = transactions_collection.count_documents({})
        transactions_with_invalid_data = transactions_collection.count_documents({
            "$or": [
                {"transaction_id": {"$type": "null"}},
                {"amount": {"$lt": 0}},
                {"type": {"$type": "null"}}
            ]
        })
        
        integrity_report["transactions"] = {
            "total": total_transactions,
            "invalid_records": transactions_with_invalid_data,
            "valid": total_transactions - transactions_with_invalid_data
        }
        
        # Overall summary
        total_records = sum([report["total"] for report in integrity_report.values()])
        total_invalid = sum([report["invalid_records"] for report in integrity_report.values()])
        total_valid = total_records - total_invalid
        
        integrity_report["summary"] = {
            "total_records": total_records,
            "valid_records": total_valid,
            "invalid_records": total_invalid,
            "data_quality_percentage": round((total_valid / total_records * 100) if total_records > 0 else 100, 2)
        }
        
        return jsonify(integrity_report), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/reports/generate", methods=["POST"])
def generate_report():
    try:
        data = request.get_json()
        report_type = data.get("report_type")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        # Generate report based on type
        if report_type == "sales":
            sales_data = list(sales_collection.find({
                "date": {"$gte": start_date, "$lte": end_date}
            }))
            total_sales = sum(sale.get("total_amount", 0) for sale in sales_data)
            
            report = {
                "type": "sales",
                "start_date": start_date,
                "end_date": end_date,
                "total_sales": total_sales,
                "total_transactions": len(sales_data),
                "data": sales_data,
                "generated_at": datetime.datetime.now()
            }
        
        elif report_type == "inventory":
            products = list(products_collection.find({}))
            report = {
                "type": "inventory",
                "total_products": len(products),
                "low_stock_items": len([p for p in products if p.get("stock_quantity", 0) < p.get("min_stock_level", 10)]),
                "data": products,
                "generated_at": datetime.datetime.now()
            }
        
        result = reports_collection.insert_one(report)
        report['_id'] = str(result.inserted_id)
        return jsonify({"message": "Report generated successfully", "report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/profile")
def profile():

    user_email = session.get("user_email")

    if not user_email:
        return redirect("/")

    user = collection.find_one({"email": user_email})

    if not user:
        return "User not found"

    return render_template("profile.html", user=user)

@app.route("/api/dashboard/data")
def dashboard_data():

    from datetime import datetime, timedelta
    from flask import request, jsonify

    # Get range from frontend
    range_value = request.args.get("range", "7")

    if range_value == "30":
        days = 30
    elif range_value == "90":
        days = 90
    else:
        days = 7

    start_date = datetime.today() - timedelta(days=days)

    products = list(db.products.find())
    sales = list(db.sales.find())

    # -------- SALES OVERVIEW --------

    sales_by_date = {}
    for i in range(days):
        day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        sales_by_date[day] = 0
    for s in sales:

        date_str = s.get("date")
        amount = s.get("total_amount", 0)

        if not date_str:
            continue

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            continue
        
        date_key = date_obj.strftime("%Y-%m-%d")

        if date_key in sales_by_date:
            sales_by_date[date_key] += amount

    # -------- INVENTORY STATUS --------

    in_stock = 0
    low_stock = 0
    out_stock = 0

    for p in products:

        stock = p.get("stock_quantity", 0)
        min_stock = p.get("min_stock_level", 5)

        if stock == 0:
            out_stock += 1

        elif stock <= min_stock:
            low_stock += 1

        else:
            in_stock += 1


    # -------- TOP PRODUCTS --------

    pipeline = [
        {
            "$group": {
                "_id": "$product_name",
                "total_sold": {"$sum": "$quantity"}
            }
        },
        {"$sort": {"total_sold": -1}},
        {"$limit": 5}
    ]

    top_products = list(db.sales.aggregate(pipeline))


    return jsonify({
        "sales_overview": sales_by_date,
        "inventory_status": {
            "in_stock": in_stock,
            "low_stock": low_stock,
            "out_stock": out_stock
        },
        "top_products": top_products
    })

@app.route("/api/dashboard/alerts")
def dashboard_alerts():

    products = list(db.products.find())
    alerts = list(db.alerts.find().sort("created_at", -1).limit(5))

    low_stock_products = []

    for p in products:

        stock = p.get("stock_quantity", 0)
        min_stock = p.get("min_stock_level", 5)

        if stock <= min_stock:

            low_stock_products.append({
                "name": p.get("name"),
                "stock": stock,
                "min_stock": min_stock
            })

    notifications = []

    for a in alerts:

        notifications.append({
            "title": a.get("alert_type", "Alert"),
            "message": a.get("message", ""),
            "time": str(a.get("created_at", ""))
        })

    return jsonify({
        "low_stock": low_stock_products,
        "notifications": notifications
    })

if __name__ == "__main__":
    app.run(debug=True)
