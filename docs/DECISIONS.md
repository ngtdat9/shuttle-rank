# Decision Log

Owned by the `orchestrator` agent. Record every decision that changes architecture, schema, API contract, dependencies, business rules, or scope. Decisions that change product behaviour or scope need the user's approval.

**Statuses:** `proposed` · `accepted` · `superseded by D-xxx` · `rejected`

**Template**

```
## D-nnn: Title
- Status:
- Date:
- Context:
- Decision:
- Consequences:
```

---

## D-001: Multi-agent development workflow
- Status: accepted
- Date: 2026-11-19
- Context: The project will be built by Cursor agents, one phase at a time.
- Decision: The `orchestrator` coordinates the `backend-engineer`, `frontend-engineer`, `qa-engineer`, and `product-ux` agents (definitions in `.cursor/agents/`). Each specialist owns specific files. Concurrent code changes use separate git worktrees on `task/<id>-<slug>` branches. The orchestrator reviews every diff, and a task is done only after QA PASS and merge.
- Consequences: Requires a git repository. `docs/TASKS.md` is the single status board.

## D-002: Modular monolith
- Status: accepted
- Date: 2026-11-19
- Context: A small club app for 6 to 10 players (`docs/BUILD_PLAN.md` section 3).
- Decision: One FastAPI backend, layered as routes → services → repositories/models, plus one Next.js frontend. No microservices.
- Consequences: The backend owns all business rules and Elo calculations.

## D-003: Database (Option A)
- Status: accepted
- Date: 2026-11-19
- Context: `docs/BUILD_PLAN.md` section 2.
- Decision: SQLite + SQLAlchemy 2.x + Alembic locally; Supabase PostgreSQL in production. Portable SQL only.
- Consequences: Schema changes always go through Alembic. PostgreSQL portability is verified in Phase 7.

## D-004: Elo parameters
- Status: accepted
- Date: 2026-11-19
- Context: `docs/BUILD_PLAN.md` section 6.
- Decision: Start 1500, K=32, divisor 400; winner-only result with no score margin; one symmetric integer delta; only completed matches count; tournament matches use the same rules; no manual rating edits; corrections replay chronologically.
- Consequences: Ratings are zero-sum across players.

## D-005: Authentication
- Status: accepted
- Date: 2026-11-19
- Context: `docs/BUILD_PLAN.md` section 7.
- Decision: Supabase Auth email/password for a single admin. The backend verifies the JWT and checks an admin allowlist it controls. No public registration. Any dev-only auth stub is isolated from production.
- Consequences: The JWT verification method (shared secret or JWKS signing keys) must be confirmed against the Supabase project in task `P3-02`.

## D-006: API contract ownership
- Status: accepted
- Date: 2026-11-19
- Context: Backend and frontend agents work in parallel.
- Decision: `docs/API.md` is the contract. The backend-engineer maintains it together with the Pydantic schemas, and the orchestrator approves changes. The frontend codes against it and never invents fields. FastAPI's OpenAPI output must match it.
- Consequences: Frontend work that consumes an endpoint starts only after that endpoint's contract is approved.

## D-007: Elo integer rounding method
- Status: accepted (autonomous build)
- Date: 2026-11-19
- Context: The plan requires one symmetric integer delta but does not specify rounding. Python's `round()` uses banker's rounding.
- Decision (proposed): `delta = floor(K * (1 - E_winner) + 0.5)`, that is, round half up computed from the winner's perspective, then apply `+delta` to the winner and `-delta` to the loser. This gives 16 at equal 1500 ratings.
- Consequences: Must be documented in `docs/ELO_ALGORITHM.md` and covered by rounding tests.

## D-008: Frontend/backend type sharing
- Status: accepted
- Date: 2026-11-19
- Context: TypeScript types must stay in sync with the Pydantic schemas.
- Decision (proposed): Start with hand-written types in `frontend/types/`, checked against `docs/API.md` in review and QA. Consider generating them from OpenAPI (for example with `openapi-typescript`) if drift becomes a problem.
- Consequences: Adds no dependency for now.

## D-009: Tooling defaults
- Status: accepted
- Date: 2026-11-19
- Context: `docs/BUILD_PLAN.md` specifies `requirements.txt` but no frontend package manager or linters.
- Decision (proposed): Backend uses `pip` + `venv` + `requirements.txt`, with Ruff for lint and format and pytest. Frontend uses `npm`, ESLint (Next.js default), and Prettier.
- Consequences: `.cursor/setup-worktree.sh` assumes `npm` and `backend/.venv`.

## D-010: Location of the build plan
- Status: accepted
- Date: 2026-11-19
- Context: The owner moved the plan to `docs/BUILD_PLAN.md`.
- Decision: All agent, rule, and doc references point to `docs/BUILD_PLAN.md`.
- Consequences: None.

---

The following decisions were made autonomously by the orchestrator during the unattended build (owner brief, 2026-11-19). The owner explicitly asked for sensible defaults without confirmation.

## D-011: Scope of the first release
- Status: accepted
- Date: 2026-11-19
- Context: `BUILD_PLAN.md` section 14 defers tournaments, monthly snapshots, and achievements. The owner's brief requires them in the first build.
- Decision: Build all of them, still in phase order: core Elo and matches first, extras after.
- Consequences: More surface to test. Avatar uploads and CSV export stay out of scope.

## D-012: Orchestrator authors the initial API contract
- Status: accepted
- Date: 2026-11-19
- Context: Backend and frontend foundations ran in parallel, and the contract is the cross-agent integration point.
- Decision: The orchestrator wrote `docs/API.md`. The backend-engineer owns it from Phase 2 onward, and changes still go through the orchestrator.
- Consequences: None.

## D-013: Match deletion is a soft delete
- Status: accepted
- Date: 2026-11-19
- Context: The brief asks for "delete a match with proper rating recalculation", while the plan says to preserve history and keep an audit trail.
- Decision: `DELETE /admin/matches/{id}` sets `matches.deleted_at`. The match is then excluded from ratings and public reads, ratings are replayed, and the action is audited.
- Consequences: Data is recoverable from the database and the audit log.

## D-014: Replay strategy
- Status: accepted
- Date: 2026-11-19
- Context: Corrections must recalculate later ratings chronologically.
- Decision: For any change that affects ratings:
  1. Find the earliest affected match position, ordered by (`match_date`, `created_at`, `id`).
  2. Restore each player's rating from before that point, using their last `rating_history.new_rating` or 1500.
  3. Delete `rating_history` rows from that point on and reprocess the later rated matches.
  4. Recompute `current_rating` and `highest_rating` from the full history, then rebuild monthly snapshots.

  All of this happens in one transaction, with an audit entry recording the previous result. A new match dated after the latest rated match is processed incrementally.
- Consequences: Simple and correct at club scale (hundreds of matches). Rating history is rebuilt only for affected matches. The audit log preserves what was there before.

## D-015: Tournament bracket storage
- Status: accepted
- Date: 2026-11-19
- Context: The plan lists tournaments and participants but not bracket slots.
- Decision: Add a `bracket_matches` table: `round`, `position`, two nullable player slots, `winner_id`, `is_bye`, and a nullable unique `match_id`. The next slot is derived as `(round + 1, position // 2)`, with slot A for even positions and slot B for odd ones. Tournament results go through the normal match service.
- Consequences: Correcting, canceling, or deleting a tournament match is only allowed while the next bracket match has no result.

## D-016: Admin allowlist and dev authentication
- Status: accepted
- Date: 2026-11-19
- Context: The plan requires a backend-controlled allowlist, plus an isolated dev stub while Supabase isn't configured. The brief lists "admin users" as an entity.
- Decision:
  - An `admin_users` table keyed by Supabase `auth_user_id` (the JWT `sub`), bootstrapped from `ADMIN_BOOTSTRAP_USER_ID`/`ADMIN_BOOTSTRAP_EMAIL` or a CLI command.
  - JWT verification uses HS256 with `SUPABASE_JWT_SECRET` if it is set, otherwise the project JWKS.
  - `AUTH_MODE=dev` accepts `DEV_ADMIN_TOKEN` only when `APP_ENV` is not `production`, and the app refuses to start otherwise.
  - On the frontend, `NEXT_PUBLIC_AUTH_MODE=dev` shows a dev-token login instead of Supabase.
- Consequences: Real Supabase login needs the owner's project credentials (an external blocker, documented).

## D-017: Dashboard aggregate endpoint
- Status: accepted
- Date: 2026-11-19
- Context: The dashboard needs leader, totals, recent matches, progression, active tournament, and recent achievements.
- Decision: Add `GET /api/v1/dashboard` so the page doesn't need many round trips. Stats such as win rate, form, and 30-day change are computed in the backend and returned by the API.
- Consequences: The frontend never derives ratings or rankings.

## D-018: App name and visual identity
- Status: accepted
- Date: 2026-11-19
- Decision: The app is "Shuttle Rank". The dark design system follows the TENOIS reference, adapted for badminton, using the tokens from the owner's brief.
- Consequences: None.

## D-019: Next.js data fetching mode
- Status: accepted
- Date: 2026-11-19
- Context: `create-next-app` 16.4 enabled the experimental `cacheComponents` and `partialPrefetching` options. With them on, every uncached fetch must sit inside a Suspense boundary or the build fails.
- Decision: Turn both options off. Public pages are server components that fetch from the API with `cache: "no-store"`, so ratings are always fresh. Interactive pieces are client components.
- Consequences: Simpler data flow. The cost is one dynamic render per request, which is negligible at club scale.
