# Shuttle Rank

A public Elo ranking site for a small badminton club (6 to 10 friends, men's singles). Anyone can browse the rankings, players, matches, head-to-head records and tournaments. A single admin records results, and the backend computes every rating.

- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts. Deployed on Vercel.
- **Backend:** FastAPI, SQLAlchemy 2.x, Alembic, Pydantic. Deployed on Render.
- **Database:** SQLite locally, Supabase PostgreSQL in production.
- **Auth:** Supabase Auth (email and password, a single allowlisted admin). A dev-token mode works locally only and is refused in production.

## Features

- **Leaderboard:** current and monthly rankings. Equal ratings share a rank (1, 2, 2, 4).
- **Player profiles:** rating progression, record, streaks, achievements and match history.
- **Match history:** filters and pagination.
- **Head-to-head:** results between any two players.
- **Tournaments:** single-elimination brackets with byes and standard seeding. Results are rated with the same Elo rules as club matches, winners advance automatically, and final positions are set when the final is recorded.
- **Achievements:** the admin can award and revoke them.
- **Admin area:** players, matches (record, correct, cancel and soft-delete, each with chronological rating replay), tournaments, achievements and an audit log of every admin write.

### Elo rules

- Every player starts at 1500, with K = 32 and divisor 400.
- Each match produces one symmetric integer delta, so ratings are zero-sum.
- Only completed matches count.
- A correction replays every match from the earliest affected point. See `docs/ELO_ALGORITHM.md`.

## Quick start (local)

```bash
# Backend (Python 3.12)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # AUTH_MODE=dev, set DEV_ADMIN_TOKEN
alembic upgrade head
python -m app.cli seed-demo --reset   # demo players, matches, tournaments, achievements
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend (Node 20+)
cd frontend
cp .env.example .env.local      # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1, NEXT_PUBLIC_AUTH_MODE=dev
npm install
npm run dev                     # http://localhost:3000; admin at /admin/login with the dev token
```

If the frontend runs on a port other than 3000, add it to the backend `CORS_ORIGINS`.

## Tests and checks

```bash
cd backend && .venv/bin/pytest -q && .venv/bin/ruff check .
TEST_DATABASE_URL=postgresql://... .venv/bin/pytest -q    # optional: run against Postgres
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```

## Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for:

- setting up Supabase
- Render (`render.yaml`, or `backend/Dockerfile`)
- Vercel
- the environment variables
- the smoke tests
- the backups

## Documentation

| File | Contents |
|---|---|
| `docs/BUILD_PLAN.md` | Requirements, architecture, phases |
| `docs/REQUIREMENTS.md`, `docs/ux/` | Acceptance criteria and page specs |
| `docs/API.md` | Backend/frontend API contract |
| `docs/ELO_ALGORITHM.md` | Rating rules and rounding |
| `docs/DECISIONS.md` | Decision log (D-001 to D-023) |
| `docs/TASKS.md` | Task board and defect log |
| `docs/DEPLOYMENT.md` | Production deployment guide |
| `docs/FINAL_REPORT.md` | What was built, how it was verified, known limitations |
| `backend/README.md` | Backend auth and CLI details |

## Development workflow

This repo is built with Claude Code subagents. The main session acts as the orchestrator, and the specialists are defined in `.claude/agents/`. See `CLAUDE.md`.
