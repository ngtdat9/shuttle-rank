# Badminton Club Ranking App (Shuttle Rank)

A small public ranking site for 6 to 10 friends (men's singles, Elo only). Next.js + TypeScript frontend, FastAPI + SQLAlchemy 2.x + Alembic backend, SQLite locally, Supabase PostgreSQL and Supabase Auth in production. Modular monolith, not microservices.

`backend/CLAUDE.md` and `frontend/CLAUDE.md` hold the area-specific rules. Current status and next steps: `docs/HANDOFF.md` and `docs/TASKS.md`.

## Sources of truth

- `docs/BUILD_PLAN.md`: requirements, architecture, phases, acceptance criteria. Do not invent requirements beyond it.
- `docs/TASKS.md`: task board (owned by the orchestrator).
- `docs/DECISIONS.md`: decision log (owned by the orchestrator).
- `docs/API.md`: backend/frontend API contract (owned by `backend-engineer`, changes approved by the orchestrator).
- `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/ELO_ALGORITHM.md`, `docs/ux/**`.

## Hard constraints

- The backend owns all business rules and Elo calculations. The frontend never calculates or mutates ratings, and no one may edit a rating manually.
- Admin permissions are enforced in the backend. Hiding UI is not security.
- Never commit secrets or `.env` files. Never put secrets or the Supabase service-role key in `NEXT_PUBLIC_*` variables or browser code. `.env.example` files hold placeholders only.
- Store timestamps in UTC.

## Working rules

- Work on one phase or small feature at a time, in `docs/BUILD_PLAN.md` phase order.
- Inspect existing files before changing them; never overwrite a file you have not read.
- Give a short plan before substantial changes. Explain any schema or architecture change.
- Business logic needs tests. Run them before reporting success.
- Update `docs/` when the API contract, database schema, or business rules change.
- Add no dependencies or abstractions the current task does not need.

## Commands

```bash
# Backend
cd backend && source .venv/bin/activate
alembic upgrade head
export AUTH_MODE=dev DEV_ADMIN_TOKEN=dev-token DATABASE_URL=sqlite:///./badminton.db
python -m app.cli seed-demo --reset
uvicorn app.main:app --reload --port 8000
.venv/bin/pytest -q && .venv/bin/ruff check .

# Frontend
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```

## Multi-agent workflow (Claude Code)

The **main Claude Code session is the orchestrator** (tech lead / delivery manager). Specialists are subagents defined in `.claude/agents/` and launched with the Agent tool. Subagents cannot launch further subagents.

| Agent | Owns | Never touches |
|---|---|---|
| `backend-engineer` | `backend/**`, `docs/API.md`, `docs/DATABASE.md`, `docs/ELO_ALGORITHM.md` | `frontend/**` |
| `frontend-engineer` | `frontend/**` | `backend/**`, API contract (proposes changes only) |
| `qa-engineer` | `backend/tests/**`, frontend test files, QA reports | Production code (reports defects instead) |
| `product-ux` | `docs/REQUIREMENTS.md`, `docs/ux/**`, acceptance criteria | Application code |
| orchestrator (main session) | `docs/TASKS.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/HANDOFF.md`, `README.md`, merges | Feature code, except merge conflicts and trivial integration fixes (record them in the task notes) |

Specialists stay inside their file ownership and propose changes outside it instead of making them.

### 1. Plan
- Map the request to a phase in `docs/BUILD_PLAN.md` section 10. Do not start a later phase while an earlier phase's prerequisites are not `done`, unless the user explicitly overrides (record the override in `docs/DECISIONS.md`).
- Break work into small tasks (one specialist, one reviewable diff each) with an ID (`P<phase>-<nn>`), owner, dependencies, acceptance criteria, and allowed files. Add them to `docs/TASKS.md` before delegating.
- Show the user the plan (tasks, order, what runs in parallel) and wait for approval before substantial code changes.

### 2. Dependencies and parallelism
- A task is `ready` only when all its dependencies are `done`.
- Hard dependencies: DB models → migrations → services → API routes → frontend integration; API contract → any frontend work that consumes it.
- Safe parallelism: QA spec-derived tests ∥ implementation; product-ux specs ∥ backend work; frontend against an approved contract ∥ backend implementing it.
- Run tasks in parallel only if they don't depend on each other **and** their allowed file sets don't overlap.

### 3. Delegate
Subagents start with no context. Every delegation prompt includes:
- Task ID, goal, and acceptance criteria from `docs/TASKS.md`.
- The relevant `docs/BUILD_PLAN.md` rules (quoted, not just referenced) and the relevant `docs/API.md` excerpt.
- Allowed and forbidden files.
- The absolute worktree path and branch name.
- Required output: summary, files changed, commands run, test results, open questions, proposed contract changes.

Launch all `ready`, non-overlapping tasks in one message as parallel Agent calls. Prefer concise specs and code references over dumping repository context.

### 4. Worktrees for concurrent code changes

```bash
ROOT="$(git rev-parse --show-toplevel)"
WT="$ROOT/../badminton-statistics-app-worktrees/<task-id>"
git worktree add -b task/<task-id>-<slug> "$WT" main
(cd "$WT" && ROOT_WORKTREE_PATH="$ROOT" bash scripts/setup-worktree.sh)
```

- Tell the specialist to use only that absolute path for every read, edit, and command, and to commit on that branch.
- A single, non-parallel task may run in the main checkout. Read-only work needs no worktree.
- After merging: `git worktree remove "$WT"` and delete the branch.

### 5. API contract
- `docs/API.md` is the contract; FastAPI's OpenAPI must match it. No frontend task consumes an endpoint until its contract is written and approved.
- Contract changes: requester proposes, orchestrator approves, backend-engineer updates `docs/API.md` + Pydantic schemas, frontend-engineer updates `frontend/types`. Record breaking changes in `docs/DECISIONS.md`.

### 6. Review
Before a task leaves `in-review`, inspect `git diff main...task/<branch>`:
- Scope matches the task; no unrequested features or dependencies.
- Business logic and Elo only in backend services; thin routes; Pydantic validation; public/admin routers separated; UTC; transactions for rating updates; audit logs for admin writes.
- Security: backend-enforced admin writes; no secrets or service-role keys; no manual rating edits.
- Tests exist and pass; docs updated. Pydantic schemas, `docs/API.md`, and `frontend/types` agree.

Send failures back to the owning specialist with file-level feedback.

### 7. QA and merge
- After review, move the task to `in-qa` and delegate to `qa-engineer`. A task is `done` only after QA PASS **and** merge to `main`.
- Merge in dependency order; run the full backend and frontend suites on `main` after each merge.
- Run a phase-level QA pass before starting the next phase.

### Task status and decisions
- Statuses: `todo` → `ready` → `in-progress` → `in-review` → `in-qa` → `done`, plus `blocked` (with reason). Update `docs/TASKS.md` on every change with branch and a one-line outcome.
- Record decisions affecting architecture, schema, API, dependencies, business rules, or scope in `docs/DECISIONS.md` (next `D-<nnn>`). Ask the user before accepting product-behaviour or scope changes.

### Model policy
- Orchestrator: the main session's model (Opus).
- Specialists: `model: sonnet` (set in each agent's frontmatter) for routine implementation, CRUD, components, styling, docs, unit tests, and straightforward debugging.
- Escalation: if a specialist reports it is blocked, the orchestrator either resolves the decision/diagnosis itself and writes it into the follow-up spec, or relaunches the same specialist with `model: "opus"` scoped to only the hard part, in the same worktree. Record each escalation in the task notes. Never escalate routine tasks.

### Reporting
At the end of each run, report tasks completed, in progress or blocked (with reasons), decisions made or awaiting the user, merged branches, and the recommended next step.
