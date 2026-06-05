from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.models import db, User, UserRole, Module

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    role_str = data.get('role', 'member')
    module_id = data.get('module_id')
    
    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400
        
    # Validate Role
    try:
        role = UserRole(role_str.lower())
    except ValueError:
        return jsonify({"msg": f"Invalid role. Must be one of: {[r.value for r in UserRole]}"}), 400
        
    # Validate Module (if provided or if role is member)
    if module_id:
        module = db.session.get(Module, module_id)
        if not module:
            return jsonify({"msg": f"Module with ID {module_id} does not exist"}), 400
    elif role == UserRole.MEMBER:
        # Members must normally belong to a module, but let's allow it to be optional 
        # or require it depending on preference. To be safe, we allow None but verify access.
        pass

    user = User(username=username, role=role, module_id=module_id)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        "msg": "User registered successfully",
        "user": user.to_dict()
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400
        
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid username or password"}), 401
        
    # Standard identity is user.id
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        "msg": "Login successful",
        "access_token": access_token,
        "user": user.to_dict()
    }), 200
