# Task Board

Owned by the `orchestrator` agent. Source of scope: `docs/BUILD_PLAN.md` section 10.

**Statuses:** `todo` → `ready` (all dependencies done) → `in-progress` → `in-review` (orchestrator reviewing the diff) → `in-qa` (qa-engineer verifying) → `done` (QA PASS and merged to `main`). `blocked` must always have a reason.

**Owners:** `orch` = orchestrator, `be` = backend-engineer, `fe` = frontend-engineer, `qa` = qa-engineer, `ux` = product-ux.

**Parallel group:** tasks in the same group of a phase have no dependency on each other and no overlapping files, so they can run at the same time in separate worktrees.

Later phases are listed at a coarse level. The orchestrator breaks them into tasks when the phase starts.

---

## Current focus

- **Phase:** 0 (project setup)
- **Next action:** `P0-01` needs user approval to run `git init`.

---

## Phase 0: Project setup

| ID | Task | Owner | Depends on | Parallel group | Status | Branch / notes |
|---|---|---|---|---|---|---|
| P0-01 | Initialize the git repo on `main`, add `.gitignore` (Python, Node, `.env*` except `.env.example`, `*.db`, build output), and make the initial commit | orch | — | — | todo | Needs user approval |
| P0-02 | Write `docs/REQUIREMENTS.md` with testable acceptance criteria derived from `docs/BUILD_PLAN.md` | ux | P0-01 | A | todo | |
| P0-03 | Scaffold the FastAPI backend: `requirements.txt`, `app/main.py`, `GET /api/v1/health`, lint/format config, `backend/.env.example` | be | P0-01 | A | todo | |
| P0-04 | Scaffold the Next.js + TypeScript frontend with Tailwind, shadcn/ui, lint/format config, minimal home page, and `frontend/.env.example` | fe | P0-01 | A | todo | |
| P0-05 | Write `docs/ARCHITECTURE.md`, plus skeletons for `docs/API.md` (with the health endpoint), `docs/DATABASE.md`, and `docs/ELO_ALGORITHM.md` | orch | P0-01 | A | todo | `docs/API.md` handed to be after this |
| P0-06 | Write `README.md` with local run commands for both apps | orch | P0-03, P0-04 | B | todo | |
| P0-07 | QA: frontend starts, backend starts, health endpoint works, `.env` is ignored, no secrets committed | qa | P0-03, P0-04, P0-06 | C | todo | |

## Phase 1: Database foundation

| ID | Task | Owner | Depends on | Parallel group | Status | Branch / notes |
|---|---|---|---|---|---|---|
| P1-01 | SQLAlchemy 2.x engine and session dependency, `DATABASE_URL` from env, SQLite foreign-key pragma | be | P0-07 | A | todo | |
| P1-02 | Models for `players`, `matches`, `rating_history`, `audit_logs` with FKs, indexes, and constraints; update `docs/DATABASE.md` | be | P1-01 | B | todo | |
| P1-03 | Alembic setup and initial migration; database can be created from empty | be | P1-02 | C | todo | |
| P1-04 | QA: test database fixtures with create/cleanup, constraint tests, models match migrations | qa | P1-03 | D | todo | |

## Phase 2: Elo engine and match processing

`P2-01` and `P2-02` only need the scaffold, so they can run in parallel with Phase 1.

| ID | Task | Owner | Depends on | Parallel group | Status | Branch / notes |
|---|---|---|---|---|---|---|
| P2-01 | Pure Elo module `services/elo.py`; document the rounding method in `docs/ELO_ALGORITHM.md` | be | P0-07, D-007 | A (with Phase 1) | todo | Rounding decision D-007 needed first |
| P2-02 | Spec-first Elo unit tests: equal ratings, unequal ratings, both winner directions, rounding, zero-sum | qa | P0-07, D-007 | A (with Phase 1) | todo | |
| P2-03 | Transactional match-processing service: validation, rating update, rating history, highest rating, duplicate prevention | be | P1-04, P2-01 | B | todo | |
| P2-04 | Chronological replay for corrected matches, with an audit log | be | P2-03 | C | todo | |
| P2-05 | QA: processing, canceled/disputed, duplicate, rollback, and replay-equals-full-recalculation tests | qa | P2-03, P2-04 | D | todo | |

## Phase 3: Core backend APIs

| ID | Task | Owner | Depends on | Parallel group | Status | Branch / notes |
|---|---|---|---|---|---|---|
| P3-01 | Write the public read contract in `docs/API.md`: rankings, players, player matches and rating history, matches, head-to-head; pagination and error shapes | be | P1-04 | A | todo | Orchestrator approval required |
| P3-02 | Admin auth dependency: Supabase JWT verification plus admin allowlist, with an isolated dev-only stub | be | P1-04 | A | todo | Separate files from P3-01 |
| P3-03 | Public read endpoints and services, implemented to the approved contract | be | P3-01, P2-05 | B | todo | |
| P3-04 | Admin player and match write endpoints with audit logging | be | P3-02, P3-03 | C | todo | |
| P3-05 | QA: API tests, contract conformance, and an authorization matrix for every admin route | qa | P3-03, P3-04 | D | todo | |

## Phase 4: Public frontend

`P4-01` only needs `P0-02` and can start during Phases 1–3. `P4-02` and `P4-03` can start once the contract (`P3-01`) is approved, before the backend is finished.

| ID | Task | Owner | Depends on | Parallel group | Status | Branch / notes |
|---|---|---|---|---|---|---|
| P4-01 | UX specs in `docs/ux/` for leaderboard, players, player profile, matches, head-to-head, and dashboard | ux | P0-02 | — | todo | |
| P4-02 | Typed API client in `frontend/lib/` and contract types in `frontend/types/` | fe | P3-01 | A | todo | |
| P4-03 | Pages: leaderboard → player directory → profile with Recharts chart → matches → head-to-head → dashboard | fe | P4-01, P4-02 | B | todo | Split per page when the phase starts |
| P4-04 | Integrate the pages with the live API and remove all mock data | fe | P3-05, P4-03 | C | todo | |
| P4-05 | QA: mobile/desktop, loading/empty/error states, no hardcoded data, contract types match | qa | P4-04 | D | todo | |

## Phase 5: Admin panel and authentication (coarse)

| ID | Task | Owner | Depends on | Status |
|---|---|---|---|---|
| P5-01 | Admin UX specs, including confirmation dialogs | ux | P4-01 | todo |
| P5-02 | Supabase Auth sign-in and admin route guard | fe | P3-02, P4-05 | todo |
| P5-03 | Admin dashboard, player management, and match recording/correction/cancellation UI | fe | P5-01, P5-02, P3-04 | todo |
| P5-04 | QA: every write route tested with admin and non-admin tokens; no secrets in bundles; corrections trigger replay | qa | P5-03 | todo |

## Phase 6: Tournaments, monthly rankings, achievements (coarse, after first version)

| ID | Task | Owner | Depends on | Status |
|---|---|---|---|---|
| P6-01 | Tournaments: models, single-elimination brackets, tournament matches through the normal match service | be | P5-04 | todo |
| P6-02 | Monthly ranking snapshots (no rating reset) | be | P5-04 | todo |
| P6-03 | Achievements: definitions and awards with duplicate prevention | be | P5-04 | todo |
| P6-04 | Tournament, monthly leaderboard, and achievement pages | fe | P6-01, P6-02, P6-03 contracts | todo |
| P6-05 | QA: brackets for different participant counts, advancement, snapshots, no duplicate awards | qa | P6-01–P6-04 | todo |

## Phase 7: Deployment (coarse)

| ID | Task | Owner | Depends on | Status |
|---|---|---|---|---|
| P7-01 | PostgreSQL portability review and Alembic migrations against Supabase | be | P5-04 | todo |
| P7-02 | Deploy the backend (Render) and frontend (Vercel); set env vars, CORS, and auth redirect URLs | orch | P7-01 | todo |
| P7-03 | Document and test backup/export and restore | be | P7-01 | todo |
| P7-04 | QA: production smoke test against the Definition of Done in `docs/BUILD_PLAN.md` section 15 | qa | P7-02, P7-03 | todo |

---

## Log

| Date | Task | Change |
|---|---|---|
| 2026-11-19 | — | Board created from `docs/BUILD_PLAN.md`. |
