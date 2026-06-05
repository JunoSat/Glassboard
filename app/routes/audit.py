from flask import Blueprint, jsonify
from app.models import AuditLog
from app.decorators import requires_role

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('/audit', methods=['GET'])
@requires_role('admin', 'manager')
def get_audit_logs():
    # Retrieve audit logs, ordered by newest first
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return jsonify([log.to_dict() for log in logs]), 200
