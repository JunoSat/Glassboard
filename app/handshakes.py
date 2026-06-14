from flask import Blueprint, request, jsonify
from app.db import get_db_connection
import mysql.connector

handshakes_bp = Blueprint('handshakes', __name__)

@handshakes_bp.route('/', methods=['POST'])
def initiate_handshake():
    """API Endpoint to log a cross-module transition request for a specific task."""
    data = request.get_json() or {}
    task_id = data.get('task_id')
    sender_id = data.get('sender_module_id')
    receiver_id = data.get('receiver_module_id')
    status = data.get('status', 'PENDING')

    # Guardrail Validation
    if not task_id or not sender_id or not receiver_id:
        return jsonify({"error": "task_id, sender_module_id, and receiver_module_id are required fields."}), 400

    if sender_id == receiver_id:
        return jsonify({"error": "A module cannot handshake with itself."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Insert the handshake tied directly to the task
        query = """
            insert into  handshakes (task_id, sender_module_id, receiver_module_id, status)
            values (%s, %s, %s, %s);
        """
        cursor.execute(query, (task_id, sender_id, receiver_id, status))
        conn.commit()

        return jsonify({"message": f"Handshake for Task #{task_id} successfully initiated."}), 201

    except mysql.connector.Error as err:
        if err.errno == 1452:
            return jsonify({"error": "Integrity Error: Specified task_id or module_id does not exist."}), 400
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()


@handshakes_bp.route('/', methods=['GET'])
def list_handshakes():
    """API Endpoint to view all ongoing handshakes with full contextual names."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Using JOINs to pull descriptive names instead of just raw IDs
        query = """
                SELECT h.id as handshake_id,
                       h.status,
                       h.requested_at,
                       t.title as task_title, 
                       m_sender.name as sender_module_name, 
                       m_receiver.name as receiver_module_name
                from handshakes h
                         join tasks t on h.task_id = t.id
                         join modules m_sender on h.sender_module_id = m_sender.id
                         join modules m_receiver on h.receiver_module_id = m_receiver.id; 
                """
        cursor.execute(query)
        all_handshakes = cursor.fetchall()
        return jsonify(all_handshakes), 200

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database failure: {err.msg}"}), 500
    finally:
        cursor.close()
        conn.close()