from datetime import datetime
from sqlalchemy import event, inspect
from flask import has_request_context
from flask_jwt_extended import current_user
from app.models import db, Handshake, AuditLog

def get_current_user_id():
    if has_request_context():
        try:
            # Check if there is an active JWT and user loaded
            if current_user and hasattr(current_user, 'id'):
                return current_user.id
        except Exception:
            # Fallback if JWT is not present in this request context
            pass
    return None

def register_listeners():
    @event.listens_for(Handshake, 'after_insert')
    def audit_handshake_insert(mapper, connection, target):
        user_id = get_current_user_id()
        action_msg = f"Handshake Requested"
        details_msg = f"Handshake ID {target.id} initiated: Module {target.sender_module_id} -> Module {target.receiver_module_id} (Status: {target.status.value if hasattr(target.status, 'value') else target.status})"
        
        connection.execute(
            AuditLog.__table__.insert().values(
                action=action_msg,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                details=details_msg
            )
        )

    @event.listens_for(Handshake, 'after_update')
    def audit_handshake_update(mapper, connection, target):
        state = inspect(target)
        status_history = state.attrs.status.history
        
        if status_history.has_changes():
            old_val = status_history.deleted[0] if status_history.deleted else "unknown"
            new_val = status_history.added[0] if status_history.added else target.status
            
            # Format status values if they are Enums
            old_status = old_val.value if hasattr(old_val, 'value') else old_val
            new_status = new_val.value if hasattr(new_val, 'value') else new_val
            
            user_id = get_current_user_id()
            action_msg = f"Handshake {new_status.capitalize()}"
            details_msg = f"Handshake ID {target.id} status updated from {old_status} to {new_status}. Module {target.sender_module_id} -> Module {target.receiver_module_id}"
            
            connection.execute(
                AuditLog.__table__.insert().values(
                    action=action_msg,
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    details=details_msg
                )
            )
