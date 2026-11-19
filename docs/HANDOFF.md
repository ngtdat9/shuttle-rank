# Handoff — Shuttle Rank (continue in Claude Code or any agent)

**Date:** 2026-11-19  
**Repo:** `/Users/thanhdat/badminton-statistics-app`  
**Branch:** `main` at `66be8a3`  
**Why:** Cursor subagents hit a usage limit mid-build. Continue from here.

## Read first

1. `docs/BUILD_PLAN.md`
2. `docs/TASKS.md` (status board + open defects BUG-01..05)
3. `docs/API.md` (contract; includes D-020 `Match.deleted_at`)
4. `docs/DECISIONS.md` (D-001..D-020)
5. `docs/REQUIREMENTS.md`, `docs/ux/*`, `docs/ELO_ALGORITHM.md`
6. `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/agents/*`

Hard rules: backend owns Elo; frontend never calculates ratings; admin writes are backend-enforced; no secrets in git or `NEXT_PUBLIC_*`.

## What is done (merged to `main`)

| Area | Notes |
|---|---|
| Project config | Multi-agent files, git, `.gitignore` |
| Backend foundation | 11 tables, Alembic, Elo ±16, health |
| Core services | Match processing, chronological replay, monthly snapshots, public GET API |
| Auth | Supabase JWT / JWKS + allowlist; `AUTH_MODE=dev` + `DEV_ADMIN_TOKEN`; rate limit; CLI `create-admin` |
| Admin API | Players, matches (create/correct/cancel/delete), stats, audit log, monthly rebuild |
| Seed | `python -m app.cli seed-demo [--reset]` (refuses in production) |
| Frontend | Design system, public pages, tournament list/detail/bracket UI, admin UI |
| Tests on `main` | **106 passed** (backend), ruff clean |

Live integration check against seeded SQLite: rankings zero-sum (8×1500=12000), leaderboard/profile/H2H correct.

## Open worktrees

```
../badminton-statistics-app-worktrees/P2-03-qa-core          # uncommitted backend/tests/qa/
../badminton-statistics-app-worktrees/P6-03a-frontend-fixes  # empty (agent died on usage)
../badminton-statistics-app-worktrees/P5-01-tournaments-achievements  # empty shell at main
```

### P2-03 (salvage)

Independent QA tests exist but are **uncommitted** under  
`../badminton-statistics-app-worktrees/P2-03-qa-core/backend/tests/qa/`:

- `reference.py`, `test_elo.py`, `test_matches.py`, `test_replay.py`, `test_monthly.py`, `test_public_api.py`, `test_persistence.py`

Agent failed with usage limit before finishing/reporting. **Action:** run those tests, fix failures or product bugs, commit on `task/P2-03-qa-core` or copy into `main`, then merge.

### P6-03a (restart)

No code was written. Re-fix BUG-01..05 from `docs/TASKS.md`:

1. **BUG-01 High** — Dashboard multi-series rating chart draws no lines  
2. **BUG-02 Medium** — Hydration mismatch (date/locale) on dashboard/profile  
3. **BUG-03 Low** — Nav wraps at 1024px  
4. **BUG-04 Low** — Leader name shown twice  
5. **BUG-05 Low** — Chart spline overshoots; use monotone/linear  
6. **D-020** — Type `Match.deleted_at` in frontend (admin UI already expects it); backend must return the field

### P5-01 (next major backend task)

Tournament + achievement **write** API. Hooks already exist:

- Inner flush-only services: `_create_match`, `_correct_match`, `_cancel_match`, `_delete_match` (see top of `backend/app/services/match_service.py`)
- Placeholder: `tournament_service.on_match_changed(...)` currently raises for tournament matches — replace with bracket updates in one transaction

Implement per `docs/API.md` Admin → Tournaments / Achievements. Then wire seed tournament data if useful.

## Recommended order

1. Salvage/finish **P2-03** QA tests.  
2. Implement **P5-01** (tournaments + achievements backend).  
3. Fix **BUG-01..05** + backend `deleted_at` on Match responses.  
4. Phase 6 full QA (auth matrix, frontend vs seeded API).  
5. Phase 7: Postgres check, `docs/DEPLOYMENT.md`, `README.md`, `docs/FINAL_REPORT.md`.

## Local commands

```bash
# Backend
cd backend
source .venv/bin/activate   # or recreate: python3.12 -m venv .venv && pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
export AUTH_MODE=dev DEV_ADMIN_TOKEN=dev-token DATABASE_URL=sqlite:///./badminton.db
python -m app.cli seed-demo --reset
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
# NEXT_PUBLIC_AUTH_MODE=dev for admin token login
npm install && npm run dev
```

Tests: `cd backend && .venv/bin/pytest -q` · `cd frontend && npm run lint && npx tsc --noEmit && npm run build`

## External blockers (do not invent credentials)

- Real Supabase project URL, JWT secret/JWKS, admin user UUID, anon key  
- Production deploy (Vercel / Render / Supabase Postgres) needs owner credentials  

Document placeholders in `.env.example` and `docs/DEPLOYMENT.md`; keep building everything that works locally with `AUTH_MODE=dev`.

## Agent note for Claude Code

Agents were ported to `.claude/agents/` (D-021). The main session is the orchestrator per `CLAUDE.md` and delegates to the Sonnet specialists. Prefer small commits. Update `docs/TASKS.md` after each milestone.
