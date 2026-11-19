# Final report: Shuttle Rank

**Date:** 2026-11-19
**Status:** Phases 0 to 7 are complete. Everything runs and is verified locally. Production deployment is not done, because it needs the owner's Supabase, Render and Vercel credentials (see `docs/DEPLOYMENT.md`).

## What was built

| Area | Delivered |
|---|---|
| Backend foundation | 11 tables, Alembic migrations, UUID keys, UTC timestamps, constraints, SQLite foreign keys |
| Elo engine | Pure functions. Starts at 1500, K=32, divisor 400, one symmetric integer delta per match, zero-sum ratings |
| Match processing | Transactional create, correct, cancel and soft-delete, each with chronological replay from the earliest affected match. Monthly snapshots |
| Public API | Dashboard, rankings (current and monthly), players, matches, head-to-head, tournaments, brackets, achievements |
| Admin API | Players, matches, tournaments (participants, bracket generation, results, bracket sync on corrections), achievements, stats, audit log, monthly rebuild. 24 admin operations, all behind backend-enforced auth |
| Auth | Supabase JWT (HS256 secret, or JWKS with ES256/RS256), a backend admin allowlist and rate limiting. A dev-token mode that production refuses |
| Frontend | Design system, all public pages, a tournament bracket view, the full admin UI with confirmation dialogs, and loading, empty and error states. Mobile-first |
| Tooling | `seed-demo` (refused in production), `create-admin` CLI, Postgres test override (`TEST_DATABASE_URL`) |
| Deployment | `render.yaml`, `backend/Dockerfile`, Supabase pooler-ready engine settings, `docs/DEPLOYMENT.md` |

## Verification

These results come from runs on `main` after the final merges, unless a row says otherwise.

| Check | Result |
|---|---|
| Backend pytest on SQLite | **398 passed** |
| Backend pytest on PostgreSQL 18.6 (P7-01 branch) | 395 passed, 1 skipped (SQLite-only PRAGMA test) |
| Ruff | Clean |
| Alembic on Postgres | Upgrade, then downgrade to base, then upgrade again; `alembic check` shows no drift |
| Frontend `lint`, `tsc --noEmit`, `next build` | All pass |
| Independent QA suite (`backend/tests/qa/`) | Core Elo, matches, replay, monthly, public API, persistence, tournaments, achievements, authorization matrix, contract and Phase 6 checks |
| Authorization matrix | All 24 admin operations tested with no token, malformed and invalid tokens, expired JWTs, bad signatures, wrong audience, `alg=none`, forged role claims, non-allowlisted users and JWKS keys. The dev token is rejected in production |
| Contract | The `app.openapi()` paths exactly match `docs/API.md`. No request schema accepts a rating field |
| Frontend vs seeded API (production build, headless Chrome) | Every public page matches the API values. There are no console or hydration errors. Tested at 390, 1024 and 1440px. Error and empty states work, admin redirects work, and a full tournament flow completed through the admin UI |
| Secrets | No service-role key, JWT secret or dev-token value appears in the browser bundle or in git |

## Defects found and fixed

| ID | Summary | Fix |
|---|---|---|
| BUG-01 | Multi-series chart showed no lines | Two independent checks couldn't reproduce it (5 of 5 lines drawn at all widths). Closed |
| BUG-02 | Hydration mismatches from date and locale formatting | Server and first paint render the same output. Dates switch to the viewer's local time after mount |
| BUG-03 | Nav wrapped at 1024px | It now fits on one row |
| BUG-04 | Leader name shown twice | It now appears once |
| BUG-05 | Chart spline overshoot | The lines were already monotone, so nothing changed |
| BUG-06 | Game scores above 99 were accepted | Scores must be 0 to 99 (R-MA-02) |
| BUG-07 | Notes over 500 characters were accepted | Enforced in both the service and the request schemas |
| BUG-08 | Rank ties were keyed on rating and wins | Ties are keyed on rating only (R-LB-02). Wins and then name still decide the row order |
| BUG-09 | Chart axis dates used UTC | They use the viewer's local timezone after mount |
| BUG-10 | Five stacked error panels on the profile page when the API is down | One page-level error, plus inline errors for individual sections |

## Known limitations and owner actions

- **Not deployed.** To go live you need a Supabase project (URL, JWT secret or JWKS, anon key, and the admin user's UUID and email), plus Render and Vercel accounts. Follow `docs/DEPLOYMENT.md`.
- **Docker image not built.** The Docker daemon wasn't running, so the image was never built. Render uses the native Python runtime in `render.yaml`, so the Dockerfile is only a fallback.
- **Dashboard wording unchecked.** The Supabase dashboard menu names in the deployment guide are from memory. Check them against the live dashboard.
- **Render settings.** `render.yaml` sets the region to `singapore`. Match it to your Supabase region. Render's free tier also has cold starts of 30 to 60 seconds.
- **Backups.** Supabase's free plan has no downloadable backups, so use the `pg_dump` command in the deployment guide.
- **Rank ties not checked visually.** The seed data has no tied ratings, so ties were only verified through the API tests.
- **No mobile Safari check.** Mobile layout was checked in headless Chrome at 390px only, not on a real device or Safari.
- **Test-order hazard.** Running Alembic in-process resets logging. The QA file restores it, but if the test order changes, add the same fixture to `conftest.py`.

## How it was built

The work was coordinated by an orchestrator agent and done by specialist agents, each in its own git worktree, with every change reviewed and QA-verified before it was merged. The agent setup started in Cursor and moved to Claude Code mid-build (D-021). The task history is in `docs/TASKS.md` and the decisions are in `docs/DECISIONS.md`.
