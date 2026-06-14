from flask import Blueprint, request, jsonify
from app.db import get_db_connection
from app.auth_utils import hash_password, verify_password
import mysql.connector

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=['POST'])
def register_user():
    """API Endpoint to securely register a new employee with a hashed password."""
    # first we need to parse the incoming json
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'member')  # Defaults to regular employee
    module_id = data.get('module_id')  # Can be NULL (unassigned)

    if not username or not password:
        return jsonify({"error": "Username and password are required fields."}), 400

    password_hash = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Returns database row results as clean Python dictionaries

    try:
        query = """
            insert into users(username, password_hashed, role, module_id) values (%s, %s, %s, %s);    
        """
        cursor.execute(query, (username, password_hash, role, module_id))
        conn.commit()
        return jsonify({"message": f"User '{username}' successfully registered."}), 201

    except mysql.connector.Error as err:
        # Handle unique constraint violation (e.g., if username already exists)
        if err.errno == 1062:
            return jsonify({"error": "Username is already taken."}), 409
        return jsonify({"error": f"Database failure: {err.msg}"}), 500

    finally:
        cursor.close()
        conn.close()


@auth_bp.route('login', methods=['POST'])
def login_user():
    """API Endpoint to authenticate an employee by verifying their bcrypt password hash."""
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
        user = cursor.fetchone()  # Get the single matching row

        if not user:
            return jsonify({"error": "Invalid username or password."}), 401

        is_valid = verify_password(password, user['password_hashed'])

        if not is_valid:
            return jsonify({"error": "Invalid username or password."}), 401

        # Success (For now, we return user metadata. Later we will attach a JWT here)
        return jsonify({
            "message": f"Welcome back, {user['username']}!",
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
