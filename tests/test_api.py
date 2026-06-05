import json
import pytest
from app.models import AuditLog, Handshake, HandshakeStatus, Task

def get_headers(client, username, password):
    """Helper to login and return auth headers."""
    res = client.post('/api/login', json={
        "username": username,
        "password": password
    })
    token = res.get_json()['access_token']
    return {"Authorization": f"Bearer {token}"}

def test_registration_and_login(client):
    # Test valid register
    res = client.post('/api/register', json={
        "username": "newuser",
        "password": "newpassword",
        "role": "member"
    })
    assert res.status_code == 201
    
    # Test duplicate username
    res = client.post('/api/register', json={
        "username": "newuser",
        "password": "newpassword"
    })
    assert res.status_code == 400
    
    # Test valid login
    res = client.post('/api/login', json={
        "username": "newuser",
        "password": "newpassword"
    })
    assert res.status_code == 200
    assert "access_token" in res.get_json()
    
    # Test invalid login
    res = client.post('/api/login', json={
        "username": "newuser",
        "password": "wrongpassword"
    })
    assert res.status_code == 401

def test_rbac_modules_and_tasks(client, seed_test_data):
    admin_headers = get_headers(client, "admin", "adminpass")
    designer_headers = get_headers(client, "designer", "designerpass")
    engineer_headers = get_headers(client, "engineer", "engineerpass")
    
    # 1. Admin/Manager should see all modules
    res = client.get('/api/modules', headers=admin_headers)
    assert res.status_code == 200
    assert len(res.get_json()) == 3
    
    # 2. Designer should only see Design module
    res = client.get('/api/modules', headers=designer_headers)
    assert res.status_code == 200
    modules = res.get_json()
    assert len(modules) == 1
    assert modules[0]['name'] == "Design"
    
    # 3. Designer should not be able to get Engineering module details
    eng_id = seed_test_data["modules"]["engineering"]
    res = client.get(f'/api/modules/{eng_id}', headers=designer_headers)
    assert res.status_code == 403
    
    # 4. Designer should not be able to add tasks to Engineering
    res = client.post('/api/tasks', json={
        "module_id": eng_id,
        "title": "Design intrusion task"
    }, headers=designer_headers)
    assert res.status_code == 403
    
    # 5. Engineer should be able to view/add tasks to Engineering
    res = client.post('/api/tasks', json={
        "module_id": eng_id,
        "title": "Engineer task"
    }, headers=engineer_headers)
    assert res.status_code == 201

def test_handshake_state_machine(client, seed_test_data):
    designer_headers = get_headers(client, "designer", "designerpass")
    engineer_headers = get_headers(client, "engineer", "engineerpass")
    tester_headers = get_headers(client, "tester", "testerpass")
    
    design_id = seed_test_data["modules"]["design"]
    eng_id = seed_test_data["modules"]["engineering"]
    qa_id = seed_test_data["modules"]["qa"]
    
    # Case A: Request handshake from Engineering to QA (Fails because Engineering has incomplete task)
    res = client.post('/api/handshake/request', json={
        "sender_module_id": eng_id,
        "receiver_module_id": qa_id
    }, headers=engineer_headers)
    assert res.status_code == 400
    assert "Some internal tasks in the sender module are incomplete" in res.get_json()['msg']
    
    # Case B: Request handshake from Design to QA (Succeeds because all Design tasks are complete)
    res = client.post('/api/handshake/request', json={
        "sender_module_id": design_id,
        "receiver_module_id": qa_id
    }, headers=designer_headers)
    assert res.status_code == 201
    handshake_id = res.get_json()['id']
    
    # Case C: Try to accept handshake using Designer credentials (should fail, Designer is not in receiver_module QA)
    res = client.post('/api/handshake/accept', json={
        "handshake_id": handshake_id
    }, headers=designer_headers)
    assert res.status_code == 403
    
    # Case D: Accept handshake using Tester credentials (should succeed, Tester is in receiver_module QA)
    res = client.post('/api/handshake/accept', json={
        "handshake_id": handshake_id
    }, headers=tester_headers)
    assert res.status_code == 200
    assert res.get_json()['status'] == 'accepted'

def test_audit_logging(client, seed_test_data):
    admin_headers = get_headers(client, "admin", "adminpass")
    designer_headers = get_headers(client, "designer", "designerpass")
    tester_headers = get_headers(client, "tester", "testerpass")
    
    design_id = seed_test_data["modules"]["design"]
    qa_id = seed_test_data["modules"]["qa"]
    
    # Initiate handshake (Design -> QA)
    res = client.post('/api/handshake/request', json={
        "sender_module_id": design_id,
        "receiver_module_id": qa_id
    }, headers=designer_headers)
    assert res.status_code == 201
    handshake_id = res.get_json()['id']
    
    # Reject handshake (QA)
    res = client.post('/api/handshake/reject', json={
        "handshake_id": handshake_id
    }, headers=tester_headers)
    assert res.status_code == 200
    
    # View audit logs as Admin
    res = client.get('/api/audit', headers=admin_headers)
    assert res.status_code == 200
    logs = res.get_json()
    
    # We should have at least 2 logs: one for Requested, one for Rejected
    assert len(logs) >= 2
    actions = [l['action'] for l in logs]
    assert "Handshake Requested" in actions
    assert "Handshake Rejected" in actions
    
    # Check that member (designer) cannot view audit logs
    res = client.get('/api/audit', headers=designer_headers)
    assert res.status_code == 403
