from flask import Blueprint, request, jsonify
from app.db import get_db_connection
import mysql.connector
from app.middleware import token_required, roles_allowed
# Create the Tasks Blueprint
tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/', methods=['POST'])
@token_required                     # Gate 1: Must be logged in with a valid token
@roles_allowed('admin', 'manager')  # Gate 2: Must be an admin or a manager to write data
def create_task(current_user):
    """API Endpoint to create an operational task assigned to a specific module."""
    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description')
    module_id = data.get('module_id')
    assigned_to = data.get('assigned_to')  # Can be NULL initially
    status = data.get('status', 'pending') # Defaults to pending

    # Input Validation
    if not title or not module_id:
        return jsonify({"error": "Title and module_id are required fields."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            insert into tasks (title, description, module_id, assigned_to, status)
            values (%s, %s, %s, %s, %s);
        """
        cursor.execute(query, (title, description, module_id, assigned_to, status))
        conn.commit()

        return jsonify({"message": f"Task '{title}' created successfully."}), 201

    except mysql.connector.Error as err:
        # Foreign key failure (e.g., if module_id doesn't exist in database)
        if err.errno == 1452:
            return jsonify({"error": "Integrity Error: Specified module_id or assigned_to user does not exist."}), 400
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()

@tasks_bp.route('/', methods=['GET'])
@token_required                     # Anyone with a valid token can view the tasks list
def list_tasks():
    """API Endpoint to fetch all active tasks in the system."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("select id, title, description, module_id, assigned_to, status from tasks;")
        all_tasks = cursor.fetchall()
        return jsonify(all_tasks), 200
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@token_required
@roles_allowed('admin', 'manager', 'member')  # All roles can update task statuses
def update_task_progress(current_user, task_id):
    """Allows engineers to update task status within their own module bounds."""
    data = request.get_json() or {}
    new_status = data.get('status')  # Expected: 'in_progress', 'completed', etc.

    if not new_status:
        return jsonify({"error": "Status field is required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Fetch the target task to verify its current module context
        cursor.execute("select module_id, title from tasks where id = %s;", (task_id,))
        task = cursor.fetchone()

        if not task:
            return jsonify({"error": "Task not found."}), 404

        # 2. RBAC Enforcement: If user is a regular member, check their module bounds
        # We need to look up which module this user belongs to in the database
        cursor.execute("select module_id from users where id = %s;", (current_user['id'],))
        user_profile = cursor.fetchone()

        if current_user['role'] == 'member':
            if not user_profile or user_profile['module_id'] != task['module_id']:
                return jsonify({
                    "error": "Access Denied: Members can only update tasks within their assigned module context."
                }), 403

        # 3. Update the task status and bind the user's ID as the worker
        query = """
            update tasks 
            set status = %s, assigned_to = %s 
            where id = %s;
        """
        cursor.execute(query, (new_status, current_user['id'], task_id))
        conn.commit()

        return jsonify({
            "message": f"Task '{task['title']}' updated to '{new_status}' by {current_user['username']}."
        }), 200

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()