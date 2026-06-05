import os
import pytest
from app import create_app
from app.models import db, Module, User, UserRole, Task
from app.config import Config

TEST_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_temp.db')

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{TEST_DB_PATH}'
    JWT_SECRET_KEY = 'test-secret-key-very-long-secret-key-32-chars'

@pytest.fixture
def app():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def seed_test_data(app):
    """Seed base modules, users, and tasks for integration tests."""
    with app.app_context():
        # Modules
        m1 = Module(name="Design", description="Design module")
        m2 = Module(name="Engineering", description="Engineering module")
        m3 = Module(name="QA", description="QA module")
        db.session.add_all([m1, m2, m3])
        db.session.commit()
        
        # Users
        admin = User(username="admin", role=UserRole.ADMIN)
        admin.set_password("adminpass")
        
        manager = User(username="manager", role=UserRole.MANAGER)
        manager.set_password("managerpass")
        
        designer = User(username="designer", role=UserRole.MEMBER, module_id=m1.id)
        designer.set_password("designerpass")
        
        engineer = User(username="engineer", role=UserRole.MEMBER, module_id=m2.id)
        engineer.set_password("engineerpass")
        
        tester = User(username="tester", role=UserRole.MEMBER, module_id=m3.id)
        tester.set_password("testerpass")
        
        db.session.add_all([admin, manager, designer, engineer, tester])
        db.session.commit()
        
        # Tasks for Design (Complete)
        t_des1 = Task(module_id=m1.id, title="UX sketch", is_complete=True)
        t_des2 = Task(module_id=m1.id, title="Wireframes", is_complete=True)
        
        # Tasks for Engineering (Incomplete)
        t_eng1 = Task(module_id=m2.id, title="Write DB models", is_complete=True)
        t_eng2 = Task(module_id=m2.id, title="Connect views", is_complete=False)
        
        db.session.add_all([t_des1, t_des2, t_eng1, t_eng2])
        db.session.commit()
        
        return {
            "modules": {"design": m1.id, "engineering": m2.id, "qa": m3.id},
            "users": {
                "admin": ("admin", "adminpass"),
                "manager": ("manager", "managerpass"),
                "designer": ("designer", "designerpass"),
                "engineer": ("engineer", "engineerpass"),
                "tester": ("tester", "testerpass")
            }
        }
