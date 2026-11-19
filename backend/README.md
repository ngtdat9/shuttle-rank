# Badminton Club Ranking API

FastAPI service for the club ranking site. It owns players, matches, Elo, and admin writes. This phase sets up the database, the health check, and the Elo formula. Match processing comes later.

Requires Python 3.12.

## Setup

From this `backend` directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

`.env.example` uses `AUTH_MODE=dev` for local development. The app refuses to start when `APP_ENV=production` and `AUTH_MODE=dev`.

## Database

Apply the schema to the database in `DATABASE_URL` (default `sqlite:///./badminton.db`):

```bash
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://127.0.0.1:8000/api/v1/health`

## Tests and lint

```bash
ruff check .
ruff format --check .
pytest
```

Tests use a temporary SQLite file. They do not open the development database.
