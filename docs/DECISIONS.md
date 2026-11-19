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
- Status: proposed (needs the user's confirmation before `P2-01`)
- Date: 2026-11-19
- Context: The plan requires one symmetric integer delta but does not specify rounding. Python's `round()` uses banker's rounding.
- Decision (proposed): `delta = floor(K * (1 - E_winner) + 0.5)`, that is, round half up computed from the winner's perspective, then apply `+delta` to the winner and `-delta` to the loser. This gives 16 at equal 1500 ratings.
- Consequences: Must be documented in `docs/ELO_ALGORITHM.md` and covered by rounding tests.

## D-008: Frontend/backend type sharing
- Status: proposed
- Date: 2026-11-19
- Context: TypeScript types must stay in sync with the Pydantic schemas.
- Decision (proposed): Start with hand-written types in `frontend/types/`, checked against `docs/API.md` in review and QA. Consider generating them from OpenAPI (for example with `openapi-typescript`) if drift becomes a problem.
- Consequences: Adds no dependency for now.

## D-009: Tooling defaults
- Status: proposed
- Date: 2026-11-19
- Context: `docs/BUILD_PLAN.md` specifies `requirements.txt` but no frontend package manager or linters.
- Decision (proposed): Backend uses `pip` + `venv` + `requirements.txt`, with Ruff for lint and format and pytest. Frontend uses `npm`, ESLint (Next.js default), and Prettier.
- Consequences: `.cursor/setup-worktree.sh` assumes `npm` and `backend/.venv`.

## D-010: Location of the build plan
- Status: proposed
- Date: 2026-11-19
- Context: The build plan is at the repo root (`docs/BUILD_PLAN.md`), but its own prompt templates refer to `docs/BUILD_PLAN.md`.
- Decision (proposed): Keep it at the root for now. If it moves to `docs/`, update the references in `.cursor/agents/`, `.cursor/rules/project.mdc`, and these docs.
- Consequences: None until it moves.
