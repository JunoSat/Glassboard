# Glassboard — Enterprise Handoff & Audit Engine

> **A self-auditing, role-enforced REST API for tracking cross-departmental task transitions — with stateless JWT authentication, a deterministic handshake state machine, and an immutable database-native audit pipeline.**

Built with **Python / Flask** · **MySQL** · **JWT** · **bcrypt**

---

## Table of Contents

1. [What Is Glassboard?](#what-is-glassboard)
2. [System Architecture Overview](#system-architecture-overview)
3. [Repository Structure](#repository-structure)
4. [File-by-File Breakdown](#file-by-file-breakdown)
5. [Database Schema](#database-schema)
6. [State Machine: The Handshake Protocol](#state-machine-the-handshake-protocol)
7. [Authentication & RBAC Flow](#authentication--rbac-flow)
8. [Audit Pipeline](#audit-pipeline)
9. [API Reference](#api-reference)
10. [Setup & Deployment](#setup--deployment)
    - [Prerequisites](#prerequisites)
    - [Windows (PowerShell)](#windows-powershell)
    - [Linux / macOS (Bash/Zsh)](#linux--macos-bashzsh)
11. [End-to-End Verification](#end-to-end-verification)
12. [Security Design Decisions](#security-design-decisions)

---

## What Is Glassboard?

Modern engineering organisations operate across specialised departments — hardware, firmware, software, QA, deployment. When a task needs to move from one team to another, the transition is almost always informal: a Slack message, a Jira comment, a verbal handoff. This creates cascading delays, accountability gaps, and audit nightmares.

Glassboard eliminates this by modelling inter-departmental task transitions as **verifiable digital handshakes**: a formal protocol requiring authenticated initiation, role-gated approval, and automatic atomic ownership transfer — with every mutation recorded immutably at the database layer, independent of the application runtime.

**Core capabilities:**

- Stateless JWT authentication with bcrypt-hashed credentials (12 rounds)
- Tiered Role-Based Access Control — `admin`, `manager`, `member`
- Deterministic handshake state machine: `PENDING → ACTIVE | REJECTED`
- Server-side status enforcement — client payloads can never forge a pre-approved handshake
- Privilege escalation prevention — registration endpoint hardcodes `member` role regardless of request body
- Automatic atomic task ownership cascade on handshake approval
- `SECRET_KEY` enforcement — server refuses to boot if the signing key is not set
- Immutable audit log written by native MySQL triggers, bypassing the application layer entirely
- Connection pool management for concurrent request handling
- Global structured error handling — the API never leaks raw Python tracebacks

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (HTTP)                            │
│          PowerShell / curl / Postman / Mobile App               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP Requests
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Application                           │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  auth.py    │  │  modules.py  │  │      tasks.py        │   │
│  │ /api/auth   │  │ /api/modules │  │     /api/tasks       │   │
│  └─────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   handshakes.py                          │   │
│  │                 /api/handshakes                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌───────────────────────┐   ┌───────────────────────────────┐  │
│  │    middleware.py       │   │         errors.py             │  │
│  │  JWT Validation        │   │   Global Exception Handlers   │  │
│  │  RBAC Enforcement      │   └───────────────────────────────┘  │
│  └───────────────────────┘                                      │
│                                                                 │
│  ┌───────────────────────┐   ┌───────────────────────────────┐  │
│  │    config.py           │   │           db.py               │  │
│  │  Environment Config    │   │  Connection Pool Management   │  │
│  │  SECRET_KEY guard      │   │  Two-phase DB bootstrap       │  │
│  └───────────────────────┘   └───────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ SQL via Connection Pool
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MySQL Server                             │
│                                                                 │
│  ┌──────────┐  ┌───────┐  ┌───────────┐  ┌──────────────────┐  │
│  │  modules │  │ users │  │   tasks   │  │   handshakes     │  │
│  └──────────┘  └───────┘  └───────────┘  └──────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    audit_log                             │   │
│  │       Written automatically by 6 MySQL Triggers          │   │
│  │       Fires on INSERT / UPDATE / DELETE — always         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
Glassboard/
│
├── app/
│   ├── auth.py            # User registration (member-locked) and JWT login
│   ├── auth_utils.py      # bcrypt hashing and verification helpers
│   ├── config.py          # Environment variable mapping — boots fail if SECRET_KEY is missing
│   ├── db.py              # MySQL connection pool + two-phase bootstrap + schema runner
│   ├── errors.py          # Global Flask error handler registration
│   ├── handshakes.py      # Handshake state machine — initiate, list, approve/reject
│   ├── middleware.py      # @token_required JWT decorator and @roles_allowed RBAC guard
│   ├── modules.py         # Operational module (department) management
│   ├── schema.sql         # Full DDL — tables, foreign keys, and 6 audit triggers
│   └── tasks.py           # Task creation, listing, and status update with module bounds
│
├── .gitignore             # Excludes .venv, __pycache__, .env
├── requirements.txt       # Pinned Python dependencies
└── run.py                 # Application factory — pool, schema, blueprints, error handlers
```

---

## File-by-File Breakdown

### `run.py` — Application Factory

The entry point. Uses Flask's **Application Factory** pattern to initialise all subsystems in the correct order before any request is served:

1. `init_pool()` — creates the MySQL connection pool
2. `execute_schema_file()` — runs `schema.sql` to ensure all tables and triggers exist (safe to re-run due to `IF NOT EXISTS` guards)
3. Registers the four API blueprints under their `/api/*` URL prefixes
4. Registers global error handlers

---

### `config.py` — Environment Configuration

Maps all sensitive values from environment variables. The most important behaviour: if `SECRET_KEY` is not set, the class raises a `RuntimeError` immediately — the server will not start. This prevents a silent fallback to a weak known key that would allow anyone to forge valid JWT tokens.

| Variable | Purpose | Default |
|---|---|---|
| `MYSQL_HOST` | Database server hostname | `localhost` |
| `MYSQL_USER` | Database username | `root` |
| `MYSQL_PASSWORD` | Database password | Fallback string — always override |
| `MYSQL_DB` | Target database name | `glassboard_db` |
| `SECRET_KEY` | JWT signing seed | **None — server refuses to boot if unset** |
| `MYSQL_POOL_SIZE` | Connection pool capacity | `5` |

---

### `db.py` — Connection Pool Management

Manages a `MySQLConnectionPool` — a set of pre-established, reusable database connections held in memory, handed out per request rather than opened fresh each time.

**Two-phase bootstrap** solves a cold-start problem: a connection pool cannot target a database that doesn't exist yet, but creating the database requires connecting first.

```
Phase 1: Raw database-less connection to MySQL server
         → CREATE DATABASE IF NOT EXISTS glassboard_db

Phase 2: Full connection pool initialised,
         targeting glassboard_db
```

`execute_schema_file()` then reads `schema.sql` and executes it statement-by-statement, idempotently creating all tables and triggers.

---

### `middleware.py` — JWT Validation & RBAC

Two **decorator factories** that protect routes without duplicating logic.

**`@token_required`**

Intercepts the request, extracts the JWT from the `Authorization: Bearer <token>` header, and verifies its cryptographic signature against `SECRET_KEY`. On success it extracts `user_id`, `username`, and `role` from the token payload and injects them into the route function as `current_user`. On failure it returns HTTP `401` immediately — the route handler never executes.

**`@roles_allowed(*roles)`**

Runs as a second layer after `@token_required`. Checks whether `current_user['role']` is in the permitted list. If not, returns HTTP `403 Forbidden`. A `member` hitting a manager-only route is rejected here before any database code runs.

Decorators must always be stacked in this order — `@token_required` on top, `@roles_allowed` directly below:

```python
@handshakes_bp.route('/<int:handshake_id>/status', methods=['PUT'])
@token_required
@roles_allowed('admin', 'manager')
def update_handshake_status(current_user, handshake_id):
    ...
```

---

### `auth.py` — Registration & Login

**`POST /api/auth/register`**

Accepts `username`, `password`, and optionally `module_id`. Regardless of what the request body contains, the role is **hardcoded to `'member'`** server-side before the database write — a caller cannot register themselves as an admin or manager.

**`POST /api/auth/login`**

Looks up the user by username, verifies the submitted password against the stored bcrypt hash, and on success issues a signed JWT valid for 24 hours. The token payload embeds `user_id`, `username`, and `role` so downstream middleware never needs to hit the database to authorise requests.

---

### `auth_utils.py` — Cryptographic Helpers

- **`hash_password(plain)`** — generates a unique random salt (12 rounds), hashes the password with bcrypt, and returns the combined string safe to store in MySQL.
- **`verify_password(plain, stored_hash)`** — extracts the embedded salt from the stored hash automatically and checks whether the plain text matches. Returns `True`/`False`. This is a one-way function — hashes are never reversed or decrypted.

---

### `modules.py` — Department Management

| Method | Route | Auth | Role |
|---|---|---|---|
| `POST` | `/api/modules/` | JWT | `admin` only |
| `GET` | `/api/modules/` | JWT | Any role |

Modules represent organisational departments. Every task and every user belongs to a module. Only admins can create them; any authenticated user can read the list. Duplicate module names return HTTP `409 Conflict`.

---

### `tasks.py` — Task Lifecycle

| Method | Route | Auth | Role |
|---|---|---|---|
| `POST` | `/api/tasks/` | JWT | `admin`, `manager` |
| `GET` | `/api/tasks/` | JWT | Any role |
| `PUT` | `/api/tasks/<id>` | JWT | `admin`, `manager`, `member` |

The `PUT` endpoint enforces an additional **module boundary check** for `member`-role users: a member can only update tasks belonging to their own module. The check queries the database live (not just the JWT) to ensure the user's module assignment hasn't changed. Admins and managers may update any task regardless of module.

When a task status is updated, the requesting user's ID is written to `assigned_to`, establishing accountability for who last acted on the task.

---

### `handshakes.py` — Cross-Module Transition Protocol

The core business logic of Glassboard. See the full [State Machine](#state-machine-the-handshake-protocol) section below.

| Method | Route | Auth | Role |
|---|---|---|---|
| `POST` | `/api/handshakes/` | JWT | Any role |
| `GET` | `/api/handshakes/` | JWT | Any role |
| `PUT` | `/api/handshakes/<id>/status` | JWT | `admin`, `manager` |

The `POST` route accepts the client payload but **immediately overwrites any `status` field with `'PENDING'`** before the database write — a caller cannot forge a pre-approved handshake by sending `{"status": "ACTIVE"}`.

The `GET` route returns fully resolved names (task title, sender module name, receiver module name) via SQL `JOIN`s, making the response human-readable without a second lookup.

---

### `errors.py` — Global Exception Handling

Registers Flask error handlers for HTTP `400`, `404`, `405`, and a catch-all for any unhandled Python exception. The API always returns structured JSON — never raw stack traces, HTML error pages, or internal path information.

---

## Database Schema

```
┌──────────────────────────────────────────────────────────────┐
│                         modules                              │
│  id (PK) │ name (UNIQUE) │ description                      │
└──────────────────┬───────────────────────────────────────────┘
                   │ referenced by users.module_id
                   │ referenced by tasks.module_id
                   │ referenced by handshakes.sender/receiver_module_id
                   │
       ┌───────────▼──────────────────────────────────────────┐
       │                       users                          │
       │  id (PK) │ username (UNIQUE) │ password_hashed       │
       │  role ENUM('admin','manager','member')               │
       │  module_id (FK → modules, ON DELETE SET NULL)        │
       └──────────────────────────────────────────────────────┘
                   │ referenced by tasks.assigned_to
       ┌───────────▼──────────────────────────────────────────┐
       │                       tasks                          │
       │  id (PK) │ title │ description │ status             │
       │  module_id (FK → modules, ON DELETE CASCADE)         │
       │  assigned_to (FK → users, ON DELETE SET NULL)        │
       └───────────────────────┬──────────────────────────────┘
                               │ referenced by handshakes.task_id
       ┌───────────────────────▼──────────────────────────────┐
       │                    handshakes                        │
       │  id (PK) │ task_id (FK) │ sender_module_id (FK)     │
       │  receiver_module_id (FK)                             │
       │  status ENUM('PENDING','ACTIVE','REJECTED')          │
       │  requested_at │ updated_at                           │
       └───────────────────────┬──────────────────────────────┘
                               │ written by MySQL Triggers
       ┌───────────────────────▼──────────────────────────────┐
       │                    audit_log                         │
       │  id │ target_table │ row_id │ action_type ENUM       │
       │  old_value │ new_value                               │
       │  changed_by_user_id (FK → users, SET NULL)           │
       │  timestamp (auto)                                    │
       └──────────────────────────────────────────────────────┘
```

**Referential integrity rules:**

- Deleting a module sets `users.module_id` to `NULL` — user is preserved, now unassigned
- Deleting a module cascades to delete its tasks and their associated handshakes
- Deleting a user sets `tasks.assigned_to` to `NULL` — task is preserved, now unowned
- Deleting a task cascades to delete its associated handshakes

---

## State Machine: The Handshake Protocol

A handshake is the formal mechanism by which a task moves between modules. It is a two-step protocol: **initiation** by any authenticated user, and **resolution** by a manager or admin only.

```
                 ┌────────────────────────────────┐
                 │   POST /api/handshakes/         │
                 │   Any authenticated user        │
                 │   status forced to PENDING      │
                 │   regardless of request body    │
                 └──────────────┬─────────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │    PENDING    │  ◄── Only valid initial state
                        └───────┬───────┘
                                │
            PUT /api/handshakes/<id>/status
            Requires: admin or manager JWT
                                │
             ┌──────────────────┴──────────────────┐
             │  action: "APPROVE"                   │  action: "REJECT"
             ▼                                      ▼
     ┌───────────────┐                    ┌─────────────────┐
     │    ACTIVE     │                    │    REJECTED     │
     └───────────────┘                    └─────────────────┘
             │
             │  Atomic cascade — single transaction:
             │  1. handshakes.status  → ACTIVE
             │  2. tasks.module_id   → receiver_module_id
             │  3. tasks.assigned_to → NULL
             ▼
  Task ownership transferred to receiving module.
  Assignment cleared — engineers in new module can claim it.
  Audit triggers fire on both the handshake and the task update.
```

**Guard rails enforced in code:**

- **Conflict guard** — once a handshake is `ACTIVE` or `REJECTED`, any further resolution attempt returns HTTP `409`. A handshake can only be processed once.
- **Self-handshake guard** — `sender_module_id == receiver_module_id` is rejected before any database write.
- **Status forgery guard** — the `status` field from the request body is read and then immediately overwritten with `'PENDING'` before insertion.
- **Cascade atomicity** — the handshake status update and task ownership transfer are committed in the same transaction. There is no intermediate state.

---

## Authentication & RBAC Flow

```
Client                             Flask                              MySQL
  │                                  │                                  │
  │  POST /api/auth/login            │                                  │
  │  { username, password }          │                                  │
  ├─────────────────────────────────►│                                  │
  │                                  │  SELECT WHERE username = ?       │
  │                                  ├─────────────────────────────────►│
  │                                  │◄─────────────────────────────────┤
  │                                  │  bcrypt.checkpw(password, hash)  │
  │                                  │  ✓ Match                         │
  │                                  │                                  │
  │                                  │  jwt.encode({                    │
  │                                  │    user_id, username, role,      │
  │                                  │    exp: now + 24h                │
  │                                  │  }, SECRET_KEY)                  │
  │◄─────────────────────────────────┤                                  │
  │  { token: "eyJh..." }            │                                  │
  │                                  │                                  │
  │  PUT /api/handshakes/3/status    │                                  │
  │  Authorization: Bearer eyJh...   │                                  │
  ├─────────────────────────────────►│                                  │
  │                                  │  @token_required:                │
  │                                  │  jwt.decode(token, SECRET_KEY)   │
  │                                  │  → { user_id:1, role:"manager" } │
  │                                  │                                  │
  │                                  │  @roles_allowed('admin','manager')│
  │                                  │  "manager" ✓ in allowed set      │
  │                                  │                                  │
  │                                  │  → handler executes              │
  │◄─────────────────────────────────┤                                  │
  │  { message: "Handshake updated" }│                                  │
```

**Role permission matrix — verified against source code:**

| Endpoint | `member` | `manager` | `admin` |
|---|:---:|:---:|:---:|
| `POST /api/auth/register` | ✓ | ✓ | ✓ |
| `POST /api/auth/login` | ✓ | ✓ | ✓ |
| `GET /api/modules/` | ✓ | ✓ | ✓ |
| `POST /api/modules/` | ✗ | ✗ | ✓ |
| `GET /api/tasks/` | ✓ | ✓ | ✓ |
| `POST /api/tasks/` | ✗ | ✓ | ✓ |
| `PUT /api/tasks/<id>` (own module only for member) | ✓\* | ✓ | ✓ |
| `POST /api/handshakes/` | ✓ | ✓ | ✓ |
| `GET /api/handshakes/` | ✓ | ✓ | ✓ |
| `PUT /api/handshakes/<id>/status` | ✗ | ✓ | ✓ |

\* Members are restricted to tasks within their own module at the database level.

---

## Audit Pipeline

The audit log is written entirely by **native MySQL triggers** — not by application code. This is a deliberate architectural choice: if the Python runtime crashes, is bypassed, or is compromised, the audit trail continues unaffected because it operates at the storage engine level.

Six triggers cover the full lifecycle of the two most critical tables:

| Trigger | Table | Event | Captures |
|---|---|---|---|
| `after_task_insert` | `tasks` | `INSERT` | New title and status |
| `after_task_update` | `tasks` | `UPDATE` | Old and new title + status |
| `after_task_delete` | `tasks` | `DELETE` | Final title and status |
| `after_handshake_insert` | `handshakes` | `INSERT` | Task ID and initial status |
| `after_handshake_update` | `handshakes` | `UPDATE` | Old and new task ID + status |
| `after_handshake_delete` | `handshakes` | `DELETE` | Final task ID and status |

Each `audit_log` row records the affected table, the row ID, the action type, the old value, the new value, and an automatic timestamp. The table is append-only from the application's perspective — there are no update or delete triggers on it — making it a tamper-evident record of system history.

---

## API Reference

All endpoints return JSON. All error responses follow the structure `{ "error": "description" }`.

### Authentication

| Method | Endpoint | Auth Required | Body |
|---|---|---|---|
| `POST` | `/api/auth/register` | None | `{ "username": "...", "password": "...", "module_id": 1 }` |
| `POST` | `/api/auth/login` | None | `{ "username": "...", "password": "..." }` |

### Modules

| Method | Endpoint | Auth Required | Allowed Roles | Body |
|---|---|---|---|---|
| `POST` | `/api/modules/` | JWT | `admin` | `{ "name": "...", "description": "..." }` |
| `GET` | `/api/modules/` | JWT | Any | — |

### Tasks

| Method | Endpoint | Auth Required | Allowed Roles | Body |
|---|---|---|---|---|
| `POST` | `/api/tasks/` | JWT | `admin`, `manager` | `{ "title": "...", "module_id": 1, "description": "...", "assigned_to": null, "status": "pending" }` |
| `GET` | `/api/tasks/` | JWT | Any | — |
| `PUT` | `/api/tasks/<id>` | JWT | Any\* | `{ "status": "in_progress" }` |

\* Members restricted to their own module.

### Handshakes

| Method | Endpoint | Auth Required | Allowed Roles | Body |
|---|---|---|---|---|
| `POST` | `/api/handshakes/` | JWT | Any | `{ "task_id": 1, "sender_module_id": 1, "receiver_module_id": 2 }` |
| `GET` | `/api/handshakes/` | JWT | Any | — |
| `PUT` | `/api/handshakes/<id>/status` | JWT | `admin`, `manager` | `{ "action": "APPROVE" }` or `{ "action": "REJECT" }` |

---

## Setup & Deployment

### Prerequisites

- **Python 3.10 or newer** — [python.org/downloads](https://www.python.org/downloads/)  
  ⚠️ On Windows, check **"Add python.exe to PATH"** during installation
- **MySQL Community Server 8.0 or newer** — [dev.mysql.com/downloads/mysql](https://dev.mysql.com/downloads/mysql/)  
  Note the `root` password you set during configuration

---

### Windows (PowerShell)

#### Step 1 — Clone or download the project

```powershell
git clone https://github.com/your-username/glassboard.git
cd glassboard
```

#### Step 2 — Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you receive an execution policy error:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then re-run the activation command.

#### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

#### Step 4 — Set environment variables

These are session-scoped. Re-run them if you open a new terminal.

```powershell
$env:MYSQL_HOST     = "127.0.0.1"
$env:MYSQL_USER     = "root"
$env:MYSQL_PASSWORD = "YourMySQLRootPasswordHere"
$env:MYSQL_DB       = "glassboard_db"
$env:SECRET_KEY     = "replace-with-a-long-random-string-minimum-32-characters"
```

Generate a strong `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

#### Step 5 — Start the server

```powershell
python run.py
```

Expected output:

```
Verifying database container existence...
DB pool initialized!
Glassboard Server online at http://127.0.0.1:5000
```

The database, all tables, and all triggers are created automatically on first boot. No manual SQL setup is required.

---

### Linux / macOS (Bash/Zsh)

#### Step 1 — Clone the project

```bash
git clone https://github.com/your-username/glassboard.git
cd glassboard
```

#### Step 2 — Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

#### Step 4 — Set environment variables

```bash
export MYSQL_HOST="127.0.0.1"
export MYSQL_USER="root"
export MYSQL_PASSWORD="YourMySQLRootPasswordHere"
export MYSQL_DB="glassboard_db"
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

To persist these across sessions, add them to your `~/.bashrc` or `~/.zshrc`.

#### Step 5 — Start the server

```bash
python run.py
```

---

## End-to-End Verification

### 1 — Register a member account (public endpoint)

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/auth/register" `
  -ContentType "application/json" `
  -Body '{"username":"alice","password":"SecurePass123","module_id":1}'
```

```bash
curl -s -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"SecurePass123","module_id":1}'
```

> Note: Role is always `member` regardless of what you send in the body.

---

### 2 — Log in and store the JWT token

```powershell
$Login = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"alice","password":"SecurePass123"}'

$Headers = @{ Authorization = "Bearer $($Login.token)" }
```

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"SecurePass123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

---

### 3 — Create two modules (requires admin token)

You'll need an admin account created directly in MySQL for the first bootstrap, or seed one via a migration script. Then:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/modules/" `
  -ContentType "application/json" `
  -Body '{"name":"Hardware Core","description":"FPGA and embedded systems."}' `
  -Headers $AdminHeaders

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/modules/" `
  -ContentType "application/json" `
  -Body '{"name":"Firmware Enclave","description":"Bootloader and low-level drivers."}' `
  -Headers $AdminHeaders
```

---

### 4 — Create a task in module 1 (requires manager or admin token)

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/tasks/" `
  -ContentType "application/json" `
  -Body '{"title":"UART Bootloader Integration","module_id":1,"status":"in_progress"}' `
  -Headers $AdminHeaders
```

---

### 5 — Initiate a handshake — transfer task 1 from module 1 to module 2

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/handshakes/" `
  -ContentType "application/json" `
  -Body '{"task_id":1,"sender_module_id":1,"receiver_module_id":2}' `
  -Headers $Headers
```

---

### 6 — Approve the handshake (requires manager or admin token)

```powershell
Invoke-RestMethod -Method Put `
  -Uri "http://127.0.0.1:5000/api/handshakes/1/status" `
  -ContentType "application/json" `
  -Body '{"action":"APPROVE"}' `
  -Headers $AdminHeaders
```

After this call:

- `handshakes` row 1: `status → ACTIVE`
- `tasks` row 1: `module_id → 2`, `assigned_to → NULL`
- `audit_log`: two new rows written automatically by MySQL triggers (one for the task update, one for the handshake update)

---

### 7 — Verify the audit trail

Connect to MySQL and inspect directly:

```sql
USE glassboard_db;
SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 20;
```

---

## Security Design Decisions

| Concern | Implementation |
|---|---|
| Password storage | bcrypt with 12 rounds and unique salt per password — never reversible |
| Authentication | Stateless JWT signed with HS256, 24-hour expiry embedded in token payload |
| `SECRET_KEY` | Server raises `RuntimeError` at boot if not set — no fallback to a known weak string |
| Privilege escalation | `register` endpoint hardcodes `role = 'member'` server-side, overriding any client-supplied value |
| Status forgery | `initiate_handshake` hardcodes `status = 'PENDING'` server-side, overriding any client-supplied value |
| SQL injection | All queries use parameterised placeholders — no string interpolation in SQL |
| Error leakage | Global error handlers ensure the API always returns structured JSON, never raw tracebacks or path info |
| Audit independence | Audit log is written by MySQL triggers — bypasses the application layer entirely |
| Module boundary | Member-role task updates verified against live DB module assignment, not just JWT claim |

**Before deploying beyond localhost:**

- Set `debug=False` in `run.py` and serve via Gunicorn or uWSGI
- Place a TLS-terminating reverse proxy (nginx, Caddy) in front — JWT tokens over plain HTTP are interceptable
- Replace the root MySQL user with a dedicated account that has only the permissions this application needs (`SELECT`, `INSERT`, `UPDATE`, `DELETE` on `glassboard_db` only)
- Consider shorter JWT expiry windows and implement refresh token rotation

---

*Glassboard — Built June 2026*
