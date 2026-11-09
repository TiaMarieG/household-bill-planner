# Household Bill Planner

A shared bill planner for a multi-person household: track recurring bills, estimate
take-home pay from hours worked, and see what's left after each payday-to-payday
week.

> This repository contains **no real financial data**. All data lives in a database
> configured through environment variables; the demo uses generated sample data.

## Stack

| Layer    | Tech                                             |
| -------- | ------------------------------------------------ |
| Backend  | Python 3.11+, FastAPI, SQLAlchemy 2              |
| Database | PostgreSQL 17 (Docker), Alembic                  |
| Frontend | React 19, Vite, React Router, TanStack Query     |
| Tests    | pytest (real Postgres), Vitest + Testing Library |

## Quick start

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running),
Python 3.11+, Node.js 20+. Works in Git Bash, PowerShell and macOS/Linux terminals.

```bash
npm run setup      # once, and again after pulling changes that add packages or migrations
npm run dev        # every time: database + API + web app, with live reload
```

- App: http://localhost:5173
- API docs: http://localhost:8000/docs

To see the app with realistic data, run `npm run seed` once (fake data only).

Press `Ctrl+C` to stop the API and web app. The database keeps running in the
background; stop it with `npm run db:stop`.

## Commands

| Command           | What it does                                                                 |
| ----------------- | ---------------------------------------------------------------------------- |
| `npm run setup`   | Creates `.env` (random local DB password) if missing, creates `backend/.venv`, installs Python and npm packages (root and frontend), starts Postgres, creates the test database, applies migrations. Safe to rerun. |
| `npm run dev`     | Starts Postgres, applies any new migrations, then runs the API and web app together. |
| `npm test`        | Runs backend (pytest) and frontend (Vitest) tests and reports both.          |
| `npm run seed`    | Fills an empty local database with fake sample data (dates relative to today). Add `-- --reset` to replace existing data. Refuses to run when `APP_ENV=production`. |
| `npm run db:stop` | Stops the Postgres container. Data is kept.                                  |

There is one `.env` in the repo root, read by both Docker Compose and the backend.
You never need to activate the virtual environment; the scripts call its Python directly.

### Resetting the database

```bash
docker compose down -v    # deletes all local data
npm run setup
```

The container creates `bill_planner` for the app; `npm run setup` and `npm run dev`
create `bill_planner_test` for tests if it is missing.

If Postgres won't start, `docker compose logs db` shows why.

## Tests

Database tests run against `TEST_DATABASE_URL`. The schema is rebuilt from the
migrations at the start of each run, and every test is rolled back afterwards.
If the database isn't running, those tests are skipped and the reason is printed.

To run one side only:

```bash
cd backend && .venv/Scripts/python -m pytest     # macOS/Linux: .venv/bin/python
cd frontend && npm test
```

## Schema changes

Run from `backend/` with the virtual environment's Python
(`.venv/Scripts/python` on Windows, `.venv/bin/python` on macOS/Linux):

```bash
python -m alembic revision --autogenerate -m "describe the change"   # review the generated file
python -m alembic upgrade head
python -m alembic check                                              # models and migrations agree
```
