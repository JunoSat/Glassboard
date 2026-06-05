import enum
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class UserRole(str, enum.Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    MEMBER = 'member'

class HandshakeStatus(str, enum.Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.MEMBER)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='SET NULL'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role.value if isinstance(self.role, enum.Enum) else self.role,
            'module_id': self.module_id
        }

class Module(db.Model):
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    tasks = db.relationship('Task', backref='module', lazy=True, cascade="all, delete-orphan")
    users = db.relationship('User', backref='module', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    is_complete = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'is_complete': self.is_complete
        }

class Handshake(db.Model):
    __tablename__ = 'handshakes'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    receiver_module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum(HandshakeStatus), nullable=False, default=HandshakeStatus.PENDING)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Specific relationship config to avoid name clashes
    sender_module = db.relationship('Module', foreign_keys=[sender_module_id], backref='sent_handshakes')
    receiver_module = db.relationship('Module', foreign_keys=[receiver_module_id], backref='received_handshakes')

    def to_dict(self):
        return {
            'id': self.id,
            'sender_module_id': self.sender_module_id,
            'receiver_module_id': self.receiver_module_id,
            'status': self.status.value if isinstance(self.status, enum.Enum) else self.status,
            'timestamp': self.timestamp.isoformat()
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    details = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'details': self.details
        }
