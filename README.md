# Glassboard - Enterprise Dependency Tracker & Handoff Engine

Glassboard is a strict dependency tracker and handoff engine between different company departments (Modules). It manages project workflows by preventing handshakes (handoffs) between departments until all internal tasks for the sending department are completely finished.

Built with **Python**, **Flask**, **SQLAlchemy (SQLite/MySQL)**, and **Flask-JWT-Extended** for authentication & role-based access control (RBAC).

---

## Project Structure

```
glassboard/
├── app/
│   ├── __init__.py          # Flask app factory, JWT config, Blueprint registration
│   ├── config.py            # SQLite / MySQL switchable configuration
│   ├── models.py            # SQLAlchemy database models (User, Module, Task, Handshake, AuditLog)
│   ├── decorators.py        # Custom authentication & RBAC authorization decorators
│   ├── listeners.py         # SQLAlchemy event listeners for automatic audit logging
│   └── routes/
│       ├── auth.py          # User authentication endpoints (/register, /login)
│       ├── modules.py       # Module & Task management endpoints
│       ├── handshakes.py    # Handshake / State machine endpoints
│       └── audit.py         # Auditing endpoints
├── tests/
│   ├── conftest.py          # Pytest fixtures and temporary database setup
│   └── test_api.py          # Integration & state machine tests
├── requirements.txt         # Package dependencies
├── seed.py                  # Database initialization and seed script
├── run.py                   # Development server entry point
└── README.md                # This manual
```

---

## Installation & Setup

1. **Clone/Navigate to the directory**:
   ```powershell
   cd c:\Users\sathv\Desktop\WorkSpace\Glassboard
   ```

2. **Install Dependencies**:
   It is recommended to use a virtual environment. Install required libraries using `pip`:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Database Swapping: SQLite to MySQL

By default, the application uses **SQLite** for rapid local development.
To switch to **MySQL** (or any other SQL dialect), simply define the `DATABASE_URL` environment variable before running the server or seed script:

```powershell
# Windows PowerShell Example
$env:DATABASE_URL="mysql+pymysql://username:password@localhost/glassboard"
```

No code changes are required.

---

## Initialize and Seed the Database

To create database schemas and seed them with dummy departments, tasks, and users, execute:

```powershell
python seed.py
```

This generates five default users with different authorization levels:
*   **Admin**: `admin` / `admin123`
*   **Manager**: `manager` / `manager123`
*   **Design Member**: `designer` / `designer123` (Module: Design)
*   **Engineering Member**: `engineer` / `engineer123` (Module: Engineering)
*   **QA Member**: `tester` / `tester123` (Module: QA)

---

## Running the Server

Start the Flask development server:

```powershell
python run.py
```
The server will run on `http://127.0.0.1:5000`.

---

## Running Automated Tests

A complete suite of integration, state machine, and audit logging tests is included. To run them, execute:

```powershell
python -m pytest
```

---

## API Documentation Reference

All endpoints (except Authentication) require a valid JWT passed in the HTTP Authorization header: `Authorization: Bearer <token>`.

### 1. Authentication Endpoints

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/register` | Public | Register a new user (`username`, `password`, `role`, `module_id`). |
| `POST` | `/api/login` | Public | Log in and return a JWT access token. |

### 2. Modules & Tasks Endpoints

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/modules` | All Users | List modules (members only see their assigned module). |
| `POST` | `/api/modules` | Admin/Manager | Create a new department module. |
| `GET` | `/api/tasks` | All Users | List tasks (members only see their module's tasks). |
| `POST` | `/api/tasks` | Write access | Create a task (members can only create tasks in their own module). |
| `PUT` | `/api/tasks/<id>` | Write access | Modify a task (e.g. toggle `is_complete`). |

### 3. Handshake Engine & State Machine

Before a module can request a handshake to another module, **all tasks in the sender module must be marked as complete (`is_complete: true`)**. Otherwise, the request will be rejected with a `400 Bad Request` error.

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/handshakes` | All Users | List handshakes (members only see those involving their module). |
| `POST` | `/api/handshake/request` | Sender Module | Initiate a handoff. Enforces completed task checks. |
| `POST` | `/api/handshake/accept` | Receiver Module | Accept the handshake. Transitions status to `accepted`. |
| `POST` | `/api/handshake/reject` | Receiver Module | Reject the handshake. Transitions status to `rejected`. |

### 4. Audit Log Endpoints

Every time a handshake transitions state (requested, accepted, rejected), an **immutable log** is automatically recorded in the database using SQLAlchemy event listeners.

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/audit` | Admin/Manager | List all audit log entries, ordered newest to oldest. |
