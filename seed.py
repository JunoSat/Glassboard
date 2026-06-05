from app import create_app
from app.models import db, Module, User, UserRole, Task, Handshake, AuditLog

def seed_db():
    app = create_app()
    with app.app_context():
        print("Dropping existing tables...")
        db.drop_all()
        
        print("Creating all tables...")
        db.create_all()
        
        print("Seeding modules...")
        design_mod = Module(name="Design", description="System architecture and UI/UX design")
        eng_mod = Module(name="Engineering", description="Core backend implementation and hardware integration")
        qa_mod = Module(name="QA", description="Quality assurance, testing, and continuous integration")
        
        db.session.add_all([design_mod, eng_mod, qa_mod])
        db.session.commit() # Commit to get IDs
        
        print("Seeding users...")
        admin = User(username="admin", role=UserRole.ADMIN)
        admin.set_password("admin123")
        
        manager = User(username="manager", role=UserRole.MANAGER)
        manager.set_password("manager123")
        
        designer = User(username="designer", role=UserRole.MEMBER, module_id=design_mod.id)
        designer.set_password("designer123")
        
        engineer = User(username="engineer", role=UserRole.MEMBER, module_id=eng_mod.id)
        engineer.set_password("engineer123")
        
        tester = User(username="tester", role=UserRole.MEMBER, module_id=qa_mod.id)
        tester.set_password("tester123")
        
        db.session.add_all([admin, manager, designer, engineer, tester])
        db.session.commit()
        
        print("Seeding tasks...")
        # Design module tasks (All complete - ready for handshake)
        t_design_1 = Task(module_id=design_mod.id, title="Draft architecture diagram", is_complete=True)
        t_design_2 = Task(module_id=design_mod.id, title="Approve UX mockups", is_complete=True)
        
        # Engineering module tasks (Incomplete)
        t_eng_1 = Task(module_id=eng_mod.id, title="Implement database models", is_complete=True)
        t_eng_2 = Task(module_id=eng_mod.id, title="Configure RBAC decorators", is_complete=False)
        t_eng_3 = Task(module_id=eng_mod.id, title="Write unit tests", is_complete=False)
        
        # QA tasks (Incomplete)
        t_qa_1 = Task(module_id=qa_mod.id, title="Define verification matrix", is_complete=False)
        
        db.session.add_all([t_design_1, t_design_2, t_eng_1, t_eng_2, t_eng_3, t_qa_1])
        db.session.commit()
        
        print("Database seeded successfully!")
        print(f"Credentials created:")
        print(f"  - admin / admin123 (Admin)")
        print(f"  - manager / manager123 (Manager)")
        print(f"  - designer / designer123 (Member - Design module)")
        print(f"  - engineer / engineer123 (Member - Engineering module)")
        print(f"  - tester / tester123 (Member - QA module)")

if __name__ == '__main__':
    seed_db()
