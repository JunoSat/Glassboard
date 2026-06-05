from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from app.models import db, Handshake, HandshakeStatus, Module, Task
from app.decorators import requires_role, verify_module_access

handshakes_bp = Blueprint('handshakes', __name__)

@handshakes_bp.route('/handshakes', methods=['GET'])
@jwt_required()
def get_handshakes():
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    
    if role_val in ('admin', 'manager'):
        handshakes = Handshake.query.all()
    else:
        # Members only see handshakes they sent or received
        member_module_id = current_user.module_id
        if not member_module_id:
            return jsonify([]), 200
            
        handshakes = Handshake.query.filter(
            (Handshake.sender_module_id == member_module_id) | 
            (Handshake.receiver_module_id == member_module_id)
        ).all()
        
    return jsonify([h.to_dict() for h in handshakes]), 200

@handshakes_bp.route('/handshake/request', methods=['POST'])
@jwt_required()
def request_handshake():
    data = request.get_json() or {}
    sender_module_id = data.get('sender_module_id')
    receiver_module_id = data.get('receiver_module_id')
    
    if not sender_module_id or not receiver_module_id:
        return jsonify({"msg": "sender_module_id and receiver_module_id are required"}), 400
        
    # Check if modules exist
    sender_module = db.session.get(Module, sender_module_id)
    receiver_module = db.session.get(Module, receiver_module_id)
    if not sender_module or not receiver_module:
        return jsonify({"msg": "Sender or Receiver module not found"}), 404
        
    # Verify module access: member can only request if they belong to sender module
    if not verify_module_access(sender_module_id):
        return jsonify({"msg": "Forbidden: cannot request handshake from another module"}), 403
        
    # Core Logic Check: Verify that all internal tasks for the sender module are marked complete
    incomplete_task = Task.query.filter_by(module_id=sender_module_id, is_complete=False).first()
    if incomplete_task:
        return jsonify({
            "msg": "Cannot initiate handshake. Some internal tasks in the sender module are incomplete.",
            "incomplete_task": incomplete_task.to_dict()
        }), 400
        
    # Create the Handshake record
    handshake = Handshake(
        sender_module_id=sender_module_id,
        receiver_module_id=receiver_module_id,
        status=HandshakeStatus.PENDING
    )
    
    db.session.add(handshake)
    db.session.commit()
    
    return jsonify(handshake.to_dict()), 201

@handshakes_bp.route('/handshake/accept', methods=['POST'])
@jwt_required()
def accept_handshake():
    data = request.get_json() or {}
    handshake_id = data.get('handshake_id')
    
    if not handshake_id:
        return jsonify({"msg": "handshake_id is required"}), 400
        
    handshake = db.session.get(Handshake, handshake_id)
    if not handshake:
        return jsonify({"msg": "Handshake not found"}), 404
        
    # Only users in the receiver_module (or admins/managers) can accept
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role_val not in ('admin', 'manager') and current_user.module_id != handshake.receiver_module_id:
        return jsonify({"msg": "Forbidden: only users in the receiver module can accept this handshake"}), 403
        
    if handshake.status != HandshakeStatus.PENDING:
        return jsonify({"msg": f"Cannot accept. Handshake is already {handshake.status.value}"}), 400
        
    handshake.status = HandshakeStatus.ACCEPTED
    db.session.commit()
    
    return jsonify(handshake.to_dict()), 200

@handshakes_bp.route('/handshake/reject', methods=['POST'])
@jwt_required()
def reject_handshake():
    data = request.get_json() or {}
    handshake_id = data.get('handshake_id')
    
    if not handshake_id:
        return jsonify({"msg": "handshake_id is required"}), 400
        
    handshake = db.session.get(Handshake, handshake_id)
    if not handshake:
        return jsonify({"msg": "Handshake not found"}), 404
        
    # Only users in the receiver_module (or admins/managers) can reject
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role_val not in ('admin', 'manager') and current_user.module_id != handshake.receiver_module_id:
        return jsonify({"msg": "Forbidden: only users in the receiver module can reject this handshake"}), 403
        
    if handshake.status != HandshakeStatus.PENDING:
        return jsonify({"msg": f"Cannot reject. Handshake is already {handshake.status.value}"}), 400
        
    handshake.status = HandshakeStatus.REJECTED
    db.session.commit()
    
    return jsonify(handshake.to_dict()), 200
