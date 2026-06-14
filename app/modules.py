from flask import Blueprint, request, jsonify
from app.db import get_db_connection
import mysql.connector

"""
This python file is for managing modules (departments)
"""

modules_bp = Blueprint("modules", __name__)

@modules_bp.route("/", methods=["POST"])
def create_module():
    """API Endpoint to spin up a new operational department module."""
    data = request.get_json() or {}
    name = data.get('name')
    description = data.get('description')

    # Input Validation
    if not name:
        return jsonify({"error": "Module name is a required field."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Parameterized query to prevent SQL injection
        query = "insert into modules (name, description) values (%s, %s);"
        cursor.execute(query, (name, description))
        conn.commit()

        return jsonify({"message": f"Operational module '{name}' created successfully."}), 201

    except mysql.connector.Error as err:
        if err.errno == 1062:  # Duplicate entry for unique module name
            return jsonify({"error": f"A module named '{name}' already exists."}), 409
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()

@modules_bp.route('/', methods=['GET'])
def list_modules():
    """API Endpoint to fetch all active modules in the system."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("select id, name, description from modules;")
        all_modules = cursor.fetchall()
        return jsonify(all_modules), 200
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()