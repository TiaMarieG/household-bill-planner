# Household Bill Planner

A shared bill planner for a multi-person household: track recurring bills, estimate
take-home pay from hours worked, and see what's left after each payday-to-payday
week.

> This repository contains **no real financial data**. All data lives in a database
> configured through environment variables; the demo uses generated sample data.

## Stack

| Layer    | Tech                                   |
| -------- | -------------------------------------- |
| Backend  | Python 3.11+, FastAPI, SQLAlchemy 2    |
| Database | PostgreSQL 17 (Docker), Alembic        |
| Frontend | React 19, Vite                         |
| Tests    | pytest (against a real Postgres)       |

## Running locally

### 1. Configure

```bash
cp .env.example .env    # then change POSTGRES_PASSWORD and both URLs to match
```

There is one `.env` in the repo root. Docker Compose and the backend both read it.

### 2. Database

```bash
docker compose up -d --wait db
```

On first start the container creates two databases: `bill_planner` for the app and
`bill_planner_test` for tests. The init script only runs when the data volume is
new; to start over, run `docker compose down -v` (this deletes all local data).

### 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate    # Windows (Git Bash). macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (requests to `/api` are proxied to the backend)

## Tests

```bash
cd backend
pytest
```

Database tests run against `TEST_DATABASE_URL`. The schema is rebuilt from the
migrations at the start of each run, and every test is rolled back afterwards.
If the database isn't running, those tests are skipped and the reason is printed.

## Schema changes

```bash
cd backend
alembic revision --autogenerate -m "describe the change"   # review the generated file
alembic upgrade head
alembic check                                              # confirms models and migrations agree
```
