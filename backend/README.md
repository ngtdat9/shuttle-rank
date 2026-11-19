# Badminton Club Ranking API

FastAPI service for the club ranking site. It owns players, matches, Elo ratings, and admin writes.

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

## Authentication

Public `GET` routes do not require a token. Every `/api/v1/admin/*` route requires `Authorization: Bearer <token>`.

### Local development

Keep `AUTH_MODE=dev` and set `DEV_ADMIN_TOKEN` to a long random string. Send that exact string as the bearer token. The actor id is `dev-admin`. An empty `DEV_ADMIN_TOKEN` rejects every admin request.

`AUTH_MODE=dev` cannot run when `APP_ENV=production`. The process refuses to start, and the admin dependency rejects that combination as well.

### Supabase

Production must use `AUTH_MODE=supabase`.

1. In the Supabase dashboard, create the single admin user by hand and turn off public sign-ups.
2. Copy the project URL into `SUPABASE_URL`.
3. Pick one signing method:
   - Legacy shared secret: set `SUPABASE_JWT_SECRET`. Tokens are verified with HS256.
   - Signing keys: leave `SUPABASE_JWT_SECRET` empty. The API loads JWKS from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` and accepts ES256 or RS256. If the secret is set, it wins and JWKS is not used.
4. `SUPABASE_JWT_AUDIENCE` defaults to `authenticated`.
5. Allowlist that user. Either set `ADMIN_BOOTSTRAP_USER_ID` to the user's UUID (the JWT `sub`) and `ADMIN_BOOTSTRAP_EMAIL` to their email, then start the API (startup upserts an active `admin_users` row when both are set), or run the CLI below.

A role claim in the token is ignored. The caller is an admin only when an active `admin_users` row has `auth_user_id` equal to `sub`.

From this directory, after `alembic upgrade head`:

```bash
python -m app.cli create-admin --auth-user-id <uuid> --email <email> --display-name "Name"
python -m app.cli list-admins
python -m app.cli deactivate-admin --auth-user-id <uuid>
```

The UUID is stored in canonical lowercase form, which is the form Supabase puts in `sub`. `create-admin` updates the existing row when that id is already present.

## Demo data

`seed-demo` loads eight players, about ten weeks of club matches, five achievement definitions, and a few awards. Match results go through the match service, so ratings are calculated rather than typed in. Pairings and scores come from `random.Random` with a fixed seed, so two runs in the same week produce the same results. Tournaments are not included.

```bash
python -m app.cli seed-demo
python -m app.cli seed-demo --reset
```

The command refuses to run when `APP_ENV=production`. It also refuses when the database already has players, unless `--reset` is set. `--reset` deletes players, matches, rating history, monthly snapshots, tournaments, brackets, achievements, awards, and audit logs, in an order foreign keys allow. It does not remove `admin_users`. `--reset` is refused in production as well, and it does not delete anything in that case.

Failed admin authentication is limited to 20 attempts per 5 minutes per client IP. Further admin requests from that IP get `429` until the window clears. Counts are kept in memory in this process, which is enough for a single Render instance. The key is the client address the server reports. Behind Render's proxy, start uvicorn with proxy headers trusted so that address is the visitor, for example `--proxy-headers --forwarded-allow-ips='*'`.

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
