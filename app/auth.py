import jwt
import datetime
from flask import Blueprint, request, jsonify
from app.db import get_db_connection
from app.auth_utils import hash_password, verify_password
from app.config import Config
import mysql.connector

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/register", methods=['POST'])
def register_user():
    """API Endpoint to securely register a new employee with a hashed password."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'member')
    module_id = data.get('module_id')

    if not username or not password:
        return jsonify({"error": "Username and password are required fields."}), 400

    # DEFEND PRIVILEGE ESCALATION: Forced lower-tier baseline assignments
    role = 'member'

    password_hash = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
                insert into users(username, password_hashed, role, module_id) \
                values (%s, %s, %s, %s); \
                """
        cursor.execute(query, (username, password_hash, role, module_id))
        conn.commit()
        return jsonify({"message": f"User '{username}' successfully registered."}), 201
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({"error": "Username is already taken."}), 409
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/login', methods=['POST'])
def login_user():
    """API Endpoint to authenticate an employee by verifying their bcrypt password hash and returning a JWT."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required fields."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = "select id, username, password_hashed, role from users where username = %s;"
        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid username or password."}), 401

        is_valid = verify_password(password, user['password_hashed'])
        if not is_valid:
            return jsonify({"error": "Invalid username or password."}), 401

        # --- GENERATING THE JWT PASSPORT ---
        # We define 'token' right here so your return statement finally has the variable it wants!
        token_payload = {
            "user_id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }

        token = jwt.encode(token_payload, Config.SECRET_KEY, algorithm="HS256")
        # --- GENERATION END ---

        # Success! Now returning your original response structure perfectly populated
        return jsonify({
            "message": f"Welcome back, {user['username']}!",
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "role": user['role']
            }
        }), 200

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()