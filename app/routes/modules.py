from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from app.models import db, Module, Task
from app.decorators import requires_role, verify_module_access

modules_bp = Blueprint('modules', __name__)

@modules_bp.route('/modules', methods=['GET'])
@jwt_required()
def get_modules():
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role_val in ('admin', 'manager'):
        modules = Module.query.all()
    else:
        # Members can only see their own module
        if current_user.module_id:
            modules = Module.query.filter_by(id=current_user.module_id).all()
        else:
            modules = []
            
    return jsonify([m.to_dict() for m in modules]), 200

@modules_bp.route('/modules/<int:module_id>', methods=['GET'])
@jwt_required()
def get_module(module_id):
    if not verify_module_access(module_id):
        return jsonify({"msg": "Forbidden: no access to this module"}), 403
        
    module = db.get_or_404(Module, module_id)
    return jsonify(module.to_dict()), 200

@modules_bp.route('/modules', methods=['POST'])
@requires_role('admin', 'manager')
def create_module():
    data = request.get_json() or {}
    name = data.get('name')
    description = data.get('description')
    
    if not name:
        return jsonify({"msg": "Module name is required"}), 400
        
    if Module.query.filter_by(name=name).first():
        return jsonify({"msg": "Module name already exists"}), 400
        
    module = Module(name=name, description=description)
    db.session.add(module)
    db.session.commit()
    
    return jsonify(module.to_dict()), 201

@modules_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    module_id = request.args.get('module_id', type=int)
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    
    if role_val in ('admin', 'manager'):
        if module_id:
            tasks = Task.query.filter_by(module_id=module_id).all()
        else:
            tasks = Task.query.all()
    else:
        # Member access limits to their assigned module
        member_module_id = current_user.module_id
        if not member_module_id:
            return jsonify([]), 200
            
        if module_id and module_id != member_module_id:
            return jsonify({"msg": "Forbidden: no access to this module's tasks"}), 403
            
        tasks = Task.query.filter_by(module_id=member_module_id).all()
        
    return jsonify([t.to_dict() for t in tasks]), 200

@modules_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    data = request.get_json() or {}
    module_id = data.get('module_id')
    title = data.get('title')
    is_complete = data.get('is_complete', False)
    
    if not module_id or not title:
        return jsonify({"msg": "module_id and title are required"}), 400
        
    if not verify_module_access(module_id):
        return jsonify({"msg": "Forbidden: cannot create task in this module"}), 403
        
    module = db.session.get(Module, module_id)
    if not module:
        return jsonify({"msg": "Module not found"}), 404
        
    task = Task(module_id=module_id, title=title, is_complete=is_complete)
    db.session.add(task)
    db.session.commit()
    
    return jsonify(task.to_dict()), 201

@modules_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    task = db.get_or_404(Task, task_id)
    if not verify_module_access(task.module_id):
        return jsonify({"msg": "Forbidden: cannot modify tasks in this module"}), 403
        
    data = request.get_json() or {}
    if 'title' in data:
        task.title = data['title']
    if 'is_complete' in data:
        task.is_complete = bool(data['is_complete'])
        
    db.session.commit()
    return jsonify(task.to_dict()), 200
