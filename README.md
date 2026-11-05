# Household Bill Planner

A shared bill planner for a multi-person household: track recurring bills, estimate
take-home pay from hours worked, and see what's left after each payday-to-payday
week.

> This repository contains **no real financial data**. All data lives in a database
> configured through environment variables; the demo uses generated sample data.

## Stack

| Layer    | Tech                         |
| -------- | ---------------------------- |
| Backend  | Python 3.11+, FastAPI        |
| Frontend | React 19, Vite               |
| Tests    | pytest                       |

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (requests to `/api` are proxied to the backend)

### Tests

```bash
cd backend
pytest
```
