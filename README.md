# Guardians Assignment - Project Registry API

A production-style MVP API for a project registry where users manage projects.

## What is implemented

- CRUD API for projects:
  - `POST /projects`
  - `GET /projects`
  - `GET /projects/{project_id}`
  - `PUT /projects/{project_id}`
  - `DELETE /projects/{project_id}`
- Required project fields:
  - `name`
  - `description`
  - `owner`
  - `expiration_date`
- JWT authentication and owner-scoped authorization
- Persistent storage with SQLite
- Containerized runtime with `docker compose up`
- Basic automated tests with `pytest`

## Architecture decisions

### 1) Framework: FastAPI

Chosen for rapid API development, strong typing, automatic validation via Pydantic, and auto-generated docs.

### 2) Persistence: SQLite + SQLAlchemy

- SQLite is enough for assignment scope and keeps setup simple.
- SQLAlchemy ORM keeps domain model and persistence cleanly separated.
- Data persists in `./data/projects.db` and is mounted as a Docker volume.

### 3) App structure

- `app/main.py` - API entrypoint and routes
- `app/models.py` - DB models
- `app/schemas.py` - request/response schemas
- `app/database.py` - engine/session wiring
- `tests/test_projects.py` - API tests

### 4) Update semantics

`PUT /projects/{project_id}` supports partial updates (MVP convenience). Empty update payload returns `400`.

### 5) Authentication/authorization implemented

- `POST /auth/token` returns a JWT bearer token.
- All `/projects` endpoints require a valid bearer token.
- User role (`alice`, `bob`) can only access their own projects.
- Admin role (`admin`) can access all projects and filter by owner.
- For non-admin users, `owner` is enforced from token identity on project creation.

### 6) Optional enhancements considered

Given the 4-hour constraint, priority was correctness, persistence, and operability. The following are good next steps:

- Authentication/authorization:
  - Add JWT/OAuth2 and enforce owner-scoped project access.
- Deployment:
  - Add CI pipeline for lint/test/build and container publish.
- Testing:
  - Add contract tests, edge-case validation, and load tests.
- Database evolution:
  - Add Alembic migrations and move to PostgreSQL for multi-user production usage.

## Optional enhancements (what to prioritize and why)

If this project is continued beyond MVP, I would prioritize the following in this order:

### 1) Authentication & authorization (highest product risk)

Why:
- Without auth, any caller can create/update/delete any project.
- Multi-user behavior is not safe without ownership boundaries.

How to include:
- Add OAuth2 password flow or external identity provider (Auth0/Entra/Okta).
- Issue JWT access tokens containing user identity (`sub`) and roles.
- Add a dependency in FastAPI to resolve current user from bearer token.
- Enforce authorization in handlers:
  - Create: `owner` derived from authenticated user.
  - Read/update/delete: user can only access own projects unless admin role.
- Add tests for `401` (missing/invalid token) and `403` (forbidden owner access).

### 2) Testing (fast confidence and safer refactoring)

Why:
- The API currently has happy-path coverage.
- Security and validation changes require stronger regression protection.

How to include:
- Keep existing integration tests and add:
  - Validation tests (empty fields, invalid dates, long values).
  - Authorization tests (owner isolation, role checks).
  - Error-path tests (`404`, empty update payload, malformed JSON).
- Add coverage reporting (`pytest-cov`) and enforce a minimum threshold in CI.

### 3) Deployment/CI-CD (repeatability and release safety)

Why:
- Interview-ready projects benefit from reproducible checks.
- Automated quality gates reduce release risk.

How to include:
- GitHub Actions pipeline on PR + main:
  - Install deps
  - Run lint/type checks
  - Run tests
  - Build Docker image
- Optional next step:
  - Push image to GHCR
  - Deploy to a small container platform (Render/Fly.io/Azure Container Apps).

### 4) Software design patterns (scalability of codebase)

Why:
- Current routes are clean for MVP, but more domain logic will increase coupling.

How to include:
- Introduce service layer pattern:
  - Route layer handles HTTP concerns.
  - Service layer handles business rules.
  - Repository layer encapsulates data access.
- Introduce unit tests at service layer for business rules without HTTP overhead.
- Add explicit DTO mapping between ORM models and API schemas for boundary clarity.

## How to run

### With Docker Compose (required)

Create environment file first:

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

API will be available at:

- `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

### Local development (optional)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
```

## Run tests

```bash
pytest -q
```

## Authentication usage

Credentials are now loaded from environment (see `.env.example`).

Test users for demo (from `.env.example`):

- `alice` / `alicepass` (user)
- `bob` / `bobpass` (user)
- `admin` / `adminpass` (admin)

Get token:

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alice&password=alicepass"
```

Use token:

```bash
curl http://localhost:8000/projects \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```