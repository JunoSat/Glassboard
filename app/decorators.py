from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, current_user
from app.models import UserRole

def requires_role(*roles):
    """
    Decorator to restrict endpoints by UserRole.
    Expects JWT token in request headers.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception as e:
                return jsonify({"msg": "Missing or invalid token", "error": str(e)}), 401
                
            if not current_user:
                return jsonify({"msg": "User not found"}), 404
                
            # Normalize role representation (string vs enum)
            role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
            
            # Admins always have access
            if role_val == UserRole.ADMIN.value:
                return fn(*args, **kwargs)
                
            if role_val not in [r.value if hasattr(r, 'value') else r for r in roles]:
                return jsonify({"msg": f"Forbidden: role '{role_val}' does not have permission"}), 403
                
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def verify_module_access(module_id):
    """
    Utility helper to check if current user has permission to access/modify a module.
    Admins and Managers have global access.
    Members only have access if they are assigned to the specified module_id.
    """
    if not current_user:
        return False
        
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role_val in (UserRole.ADMIN.value, UserRole.MANAGER.value):
        return True
        
    if module_id is None:
        return False
        
    return current_user.module_id == int(module_id)
