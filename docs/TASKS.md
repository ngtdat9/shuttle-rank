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
| P2-03 | Spec-first QA tests: Elo, matches, replay, rankings, head-to-head | qa | P1-01, P1-04 | DONE | Tests derived from the contract | Merged. 43 QA tests in `backend/tests/qa/`; 3 product defects found (BUG-06..08), tracked as strict xfails, fixed in P2-04 |
| P2-04 | Fix QA defects BUG-06..08 (score 0–99, notes ≤500, rating-only rank ties) and remove xfails | be | P2-03, P5-01 | TODO | xfails removed and passing | — |

## Phase 3: Authentication and admin backend

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P3-01 | Auth: Supabase JWT (HS256 secret or JWKS), `admin_users` allowlist, isolated dev mode, rate limit, admin bootstrap CLI | be | P1-01 | COMPLETED | 401/403/429 behaviour; dev mode refused in production | pytest 64 passed; ruff clean; orchestrator security review OK. Ran in parallel with P2-01 |
| P3-02 | Admin player and match endpoints with audit logs; admin stats and audit-log endpoints | be | P3-01 | COMPLETED | Writes audited; manual rating edits impossible | 106 passed on `main` after merge; ruff clean; seeded temp server: rankings 200, admin stats 200 with token, 401 without |
| P3-03 | Dev seed script (`python -m app.cli seed-demo`), refused in production | be | P3-02 | COMPLETED | Seeds through services, not raw ratings | `seed-demo` is reproducible, refuses in production; covered by tests |

## Phase 4: Public frontend

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P4-01 | Typed API client and contract types | fe | P1-02, P1-04 | REVIEW | Types match `docs/API.md` | — |
| P4-02 | Dashboard, leaderboard, monthly leaderboard, players directory, player profile, matches list and detail, head-to-head, with real API calls and loading, empty, and error states | fe | P4-01, P1-03 | REVIEW | No mock data; mobile and desktop | lint, tsc, build pass; routes return 200 with an error state when the API is down. Live-data integration check pending P2-01. Merged |

## Phase 5: Tournaments, monthly rankings, achievements, admin UI

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P5-01 | Tournament service: participants, bracket generation (byes, seeding), progression through the match service; achievements service and endpoints | be | P3-02 | IN_PROGRESS | Byes, odd counts, advancement, final positions; no duplicate awards | — |
| P5-02 | Tournament list and detail with bracket; achievements on profile and dashboard | fe | P4-02, P5-01 contract | REVIEW | Bracket readable on desktop and mobile | lint, tsc, build pass; error states verified with the API down; bracket samples for 5 and 8 players reviewed. Merged. Live check pending tournament backend (P5-01) |
| P5-03 | Admin UI: login (Supabase and dev), route guard, admin dashboard, players, matches (record, correct, cancel, delete with confirmations), tournaments, achievements, audit log | fe | P4-01, P3-02 | REVIEW | Admin-only; confirmations on rating-affecting actions | lint, tsc, build pass; login and route guard checked in the browser. Orchestrator fixed dynamic `process.env[name]` reads that broke Supabase mode in the browser; verified the values are inlined in the bundle. Merged. Live admin flows pending P3-02 |

## Phase 6: Integration and quality

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P6-01 | Backend QA: every endpoint, authorization matrix, persistence, tournaments | qa | P5-01 | TODO | `BUILD_PLAN.md` section 11 plus the brief's section 9 | — |
| P6-02 | Frontend QA: navigation, integration against the seeded backend, states, responsive layouts, admin protection, production build | qa | P5-02, P5-03 | TODO | All pages work against the real API | — |
| P6-03 | Fix defects found in QA | be/fe | P6-01, P6-02 | TODO | QA re-verification passes | — |

### Defects found by orchestrator integration check (2026-11-19, live API + seeded temp DB)

| ID | Defect | Severity | Fix task | Status |
|---|---|---|---|---|
| BUG-01 | Dashboard multi-player `RatingChart` draws no lines (legend only); single-series profile chart works | High | P6-03 | TODO |
| BUG-02 | Hydration mismatch warnings in dev on dashboard (`components/club/dashboard-view.tsx` around line 165, date/locale formatting) and player profile (5 issues) | Medium | P6-03 | TODO |
| BUG-03 | Desktop header nav wraps to two rows at 1024px width | Low | P6-03 | TODO |
| BUG-04 | Dashboard leader card shows the player name twice (heading and avatar label) | Low | P6-03 | TODO |
| BUG-05 | Rating chart curve overshoots below and above real values (spline); use monotone or linear | Low | P6-03 | TODO |
| BUG-06 | `game_scores` sides above 99 accepted (R-MA-02); `match_service._validate_game_scores` | Medium | P2-04 | TODO |
| BUG-07 | Notes over 500 chars accepted (R-MA-02); `match_service._validate_notes` (check PATCH too) | Medium | P2-04 | TODO |
| BUG-08 | Rank ties keyed on (rating, wins) instead of rating only (R-LB-02, OQ-10); `ranking_service.compute_standings`, `monthly_service._assign_ranks` | Medium | P2-04 | TODO |

Verified working: dashboard data, leaderboard (form ordering, shared ranks, deltas), player profile, head-to-head totals, all public routes return 200 against the live API, and zero-sum ratings (8 players sum to 12000).

## Phase 7: Deployment preparation

| ID | Task | Agent | Depends on | Status | Acceptance criteria | Test results |
|---|---|---|---|---|---|---|
| P7-01 | Postgres portability check (Docker Postgres if available), Dockerfile, `render.yaml`, Vercel config, env documentation, `docs/DEPLOYMENT.md` | be/orch | P6-03 | TODO | Migrations run on Postgres; config complete | — |
| P7-02 | `README.md`, `docs/FINAL_REPORT.md` | orch | P7-01 | TODO | Accurate, with real test results | — |

---

## Log

| Date | Task | Change |
|---|---|---|
| 2026-11-19 | P3-02 | Merged admin API/seed. |
| 2026-11-19 | P2-03 | QA agent usage-limited; WIP tests on `task/P2-03-qa-core`. |
| 2026-11-19 | P6-03a | Frontend fix agent usage-limited; no code written. Restart from HANDOFF. |
| 2026-11-19 | — | Cursor usage exhausted; handoff written to `docs/HANDOFF.md` for Claude Code. |

## Log (earlier)

| Date | Task | Change |
|---|---|---|
| 2026-11-19 | — | Board rebuilt for the autonomous build; statuses per the owner's brief. |
| 2026-11-19 | P1-01, P1-02, P1-03 | Launched in parallel (backend and frontend in separate worktrees). |
| 2026-11-19 | P1-04 | API contract written by the orchestrator. |
