# Task Board

Owned by the `orchestrator`. Scope: `docs/BUILD_PLAN.md` plus the owner's autonomous-build brief of 2026-11-19, which mirrors the BUILD_PLAN phases with tournaments, monthly rankings, and achievements pulled into the first release.

**Statuses:** `TODO` · `IN_PROGRESS` · `REVIEW` (orchestrator review or QA) · `COMPLETED` (reviewed, QA passed, merged to `main`) · `BLOCKED` (always with a reason)

**Agents:** `orch` orchestrator (Claude Opus 5.5) · `be` backend-engineer, `fe` frontend-engineer, `qa` qa-engineer, `ux` product-ux (all Grok 4.7)

**Worktrees:** `../badminton-statistics-app-worktrees/<task-id>` on branch `task/<task-id>`

---

## Phase 1: Foundation

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P1-00 | Git init, `.gitignore`, path fixes, initial commit | orch | — | COMPLETED | Repo on `main`; `.env*` and `*.db` ignored | Commit `22c6ed0` |
| P1-01 | Backend foundation: FastAPI, config, SQLAlchemy, all 11 models, Alembic initial migration, health endpoint, error format, pure Elo module and tests | be | P1-00 | COMPLETED | `alembic upgrade head` / `downgrade base` work on empty SQLite; FKs enforced; Elo ±16 at 1500; ruff and pytest pass | pytest 26 passed; ruff clean; alembic up/down OK; health 200. Orchestrator fixed migration boolean defaults for Postgres. Merged `c6b4ff2` |
| P1-02 | Frontend foundation: Next.js + TS + Tailwind + shadcn/ui + Recharts + lucide, design tokens, app shell and nav, shared components, `/design` showcase | fe | P1-00 | COMPLETED | lint, tsc, and build pass; design tokens match the brief; responsive nav | lint, tsc, build pass; `/` and `/design` 200; visually reviewed. Orchestrator disabled `cacheComponents` (D-019). Merged `4da4c82` |
| P1-03 | `docs/REQUIREMENTS.md`, `docs/ux/design-system.md`, `docs/ux/pages.md` | ux | P1-00 | COMPLETED | Testable acceptance criteria; per-page layout, fields, and states | 795 lines; aligned with `docs/API.md`, no contract changes |
| P1-04 | API contract `docs/API.md` | orch | P1-00 | COMPLETED | Every public and admin endpoint, schema, error, and rule | Reviewed against the brief |

## Phase 2: Core business logic and public API

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P2-01 | Player service and match processing: transactional rating updates, rating history, duplicate prevention, chronological replay (backdated, correct, cancel, delete), monthly snapshot rebuild, stats/ranking/head-to-head services | be | P1-01, P1-04 | COMPLETED | Contract business rules; replay equals full recalculation | Branch: 54 passed. On `main` after merging with P3-01: 92 passed, ruff clean. Orchestrator reviewed the replay engine |
| P2-02 | Public read endpoints (dashboard, rankings, monthly, players, matches, head-to-head, achievements read) | be | P2-01 | COMPLETED | Responses match `docs/API.md` | — |
| P2-03 | Spec-first QA tests: Elo, matches, replay, rankings, head-to-head | qa | P1-01, P1-04 | IN_PROGRESS | Tests derived from the contract | — |

## Phase 3: Authentication and admin backend

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P3-01 | Auth: Supabase JWT (HS256 secret or JWKS), `admin_users` allowlist, isolated dev mode, rate limit, admin bootstrap CLI | be | P1-01 | COMPLETED | 401/403/429 behaviour; dev mode refused in production | pytest 64 passed; ruff clean; orchestrator security review OK. Ran in parallel with P2-01 |
| P3-02 | Admin player and match endpoints with audit logs; admin stats and audit-log endpoints | be | P3-01 | IN_PROGRESS | Writes audited; manual rating edits impossible | — |
| P3-03 | Dev seed script (`python -m app.cli seed-demo`), refused in production | be | P3-02 | IN_PROGRESS | Seeds through services, not raw ratings | — (combined with P3-02) |

## Phase 4: Public frontend

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P4-01 | Typed API client and contract types | fe | P1-02, P1-04 | REVIEW | Types match `docs/API.md` | — |
| P4-02 | Dashboard, leaderboard, monthly leaderboard, players directory, player profile, matches list and detail, head-to-head, with real API calls and loading, empty, and error states | fe | P4-01, P1-03 | REVIEW | No mock data; mobile and desktop | lint, tsc, build pass; routes return 200 with an error state when the API is down. Live-data integration check pending P2-01. Merged |

## Phase 5: Tournaments, monthly rankings, achievements, admin UI

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P5-01 | Tournament service: participants, bracket generation (byes, seeding), progression through the match service; achievements service and endpoints | be | P3-02 | TODO | Byes, odd counts, advancement, final positions; no duplicate awards | — |
| P5-02 | Tournament list and detail with bracket; achievements on profile and dashboard | fe | P4-02, P5-01 contract | IN_PROGRESS | Bracket readable on desktop and mobile | — |
| P5-03 | Admin UI: login (Supabase and dev), route guard, admin dashboard, players, matches (record, correct, cancel, delete with confirmations), tournaments, achievements, audit log | fe | P4-01, P3-02 | IN_PROGRESS | Admin-only; confirmations on rating-affecting actions | — |

## Phase 6: Integration and quality

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P6-01 | Backend QA: every endpoint, authorization matrix, persistence, tournaments | qa | P5-01 | TODO | `BUILD_PLAN.md` section 11 plus the brief's section 9 | — |
| P6-02 | Frontend QA: navigation, integration against the seeded backend, states, responsive layouts, admin protection, production build | qa | P5-02, P5-03 | TODO | All pages work against the real API | — |
| P6-03 | Fix defects found in QA | be/fe | P6-01, P6-02 | TODO | QA re-verification passes | — |

## Phase 7: Deployment preparation

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P7-01 | Postgres portability check (Docker Postgres if available), Dockerfile, `render.yaml`, Vercel config, env documentation, `docs/DEPLOYMENT.md` | be/orch | P6-03 | TODO | Migrations run on Postgres; config complete | — |
| P7-02 | `README.md`, `docs/FINAL_REPORT.md` | orch | P7-01 | TODO | Accurate, with real test results | — |

---

## Log

| Date | Task | Change |
|---|---|---|
| 2026-11-19 | — | Board rebuilt for the autonomous build; statuses per the owner's brief. |
| 2026-11-19 | P1-01, P1-02, P1-03 | Launched in parallel (backend and frontend in separate worktrees). |
| 2026-11-19 | P1-04 | API contract written by the orchestrator. |
