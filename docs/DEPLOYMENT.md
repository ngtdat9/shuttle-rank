# Deployment guide

Production stack: Supabase (PostgreSQL + Auth), Render (FastAPI backend), Vercel (Next.js frontend).
Follow the steps in order. The backend must be live before the frontend is configured, and the Vercel URL must be known before CORS is finalised.

Security rules that apply throughout:

- Never commit `.env` files or real secrets. Only `.env.example` files with placeholders are committed.
- Never put the database URL, the JWT secret, or the Supabase service-role key in any `NEXT_PUBLIC_*` variable. The service-role key is not used by this app at all.
- The backend refuses to start with `APP_ENV=production` and `AUTH_MODE=dev`.

## What the owner must provide (checklist)

- [ ] A Supabase account and a new project (region near the Render region).
- [ ] The database password chosen at project creation.
- [ ] Supabase project URL (`https://<ref>.supabase.co`).
- [ ] Supabase anon (publishable) key. Public by design.
- [ ] JWT verification choice: legacy JWT secret (HS256), or nothing if the project uses asymmetric signing keys (JWKS).
- [ ] The admin's email and password, created in Supabase Auth, and the admin's user UUID.
- [ ] A Render account (GitHub connected to this repository).
- [ ] A Vercel account (GitHub connected to this repository).
- [ ] Optional: a custom domain, if the Vercel domain is not wanted.

## 1. Supabase

### 1.1 Create the project

1. In the Supabase dashboard choose New project. Pick a region, set a strong database password, and store it in a password manager.
2. Authentication > Sign In / Providers: keep Email enabled and turn off "Allow new users to sign up". Only the single admin exists.

### 1.2 Database connection string

Project Settings > Database > Connection string (or the Connect button). Three variants exist:

| Variant | Host and port | Use |
| --- | --- | --- |
| Direct | `db.<ref>.supabase.co:5432` | IPv6 only on the free tier. Render's free tier is IPv4, so it usually cannot connect. |
| Session pooler | `aws-0-<region>.pooler.supabase.com:5432`, user `postgres.<ref>` | Recommended for both migrations and the running API. Supports DDL. IPv4 compatible. |
| Transaction pooler | `aws-0-<region>.pooler.supabase.com:6543`, user `postgres.<ref>` | Works for the running API (the backend disables prepared statements). Do not use for migrations. |

Use the session pooler string for `DATABASE_URL` on Render. Because the start command runs `alembic upgrade head` on the same connection string, the same value serves migrations and runtime.

Format:

```
postgresql://postgres.<ref>:<URL-ENCODED-PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

- Paste the string exactly as above. The backend rewrites `postgres://` and `postgresql://` to the `postgresql+psycopg://` driver automatically, so no manual change is needed.
- URL-encode special characters in the password (`@` becomes `%40`, `/` becomes `%2F`, and so on).

### 1.3 JWT verification and keys

Project Settings > API (or JWT Keys):

- Project URL: `SUPABASE_URL` (backend) and `NEXT_PUBLIC_SUPABASE_URL` (frontend).
- anon / publishable key: `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Public. Never use the `service_role` key anywhere.
- Backend token verification, pick one:
  - Legacy JWT secret (HS256): copy the legacy JWT secret into `SUPABASE_JWT_SECRET`.
  - Asymmetric signing keys (JWKS, ES256 or RS256): leave `SUPABASE_JWT_SECRET` empty. The backend loads `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. If the secret is set it wins and JWKS is not used.

### 1.4 Create the admin user

1. Authentication > Users > Add user > Create new user. Enter the admin email and password and tick Auto Confirm User.
2. Copy the user's UUID from the users table. It is the JWT `sub` and the value for the allowlist.

## 2. Render (backend)

The repository root has `render.yaml`, a Blueprint for one web service rooted at `backend`.

1. Render dashboard > New > Blueprint, select this repository, and apply. Alternatively create a Web Service manually with root directory `backend`, runtime Python 3, and the build and start commands below.
2. Fill in the variables marked "set in dashboard" (declared with `sync: false`, so no secret is stored in git).

Commands (already in `render.yaml`):

- Build: `pip install -r requirements.txt`
- Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/v1/health` (returns 200 `{"status":"ok","database":"ok"}`, or 503 when the database is unreachable)

### Backend environment variables

| Variable | Required in production | Default | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | yes | `development` | Set to `production` (preset in `render.yaml`). Allowed: `development`, `test`, `production`. |
| `AUTH_MODE` | yes | `supabase` | Must be `supabase`. `dev` is rejected when `APP_ENV=production`. |
| `DATABASE_URL` | yes | `sqlite:///./badminton.db` | Supabase session pooler string from 1.2. Secret. |
| `CORS_ORIGINS` | yes | `http://localhost:3000` | Comma-separated exact origins, no trailing slash, e.g. `https://your-app.vercel.app`. Add a custom domain as a second entry. |
| `SUPABASE_URL` | yes | empty | `https://<ref>.supabase.co`. Used for JWKS lookup. |
| `SUPABASE_JWT_SECRET` | only for HS256 | empty | Legacy JWT secret. Leave empty to use JWKS. Secret. |
| `SUPABASE_JWT_AUDIENCE` | no | `authenticated` | Preset in `render.yaml`. |
| `DEV_ADMIN_TOKEN` | no | empty | Dev only. Do not set in production. |
| `ADMIN_BOOTSTRAP_USER_ID` | optional | empty | Admin UUID. With the email below, startup upserts an active admin row. |
| `ADMIN_BOOTSTRAP_EMAIL` | optional | empty | Admin email. Both bootstrap values must be set for the upsert to run. |
| `PORT` | injected by Render | none | Not read by the app; used by the start command. |
| `PYTHON_VERSION` | Render only | none | Preset to a 3.12 release in `render.yaml`. |

Admin authorization is by an active row in `admin_users` whose `auth_user_id` equals the token `sub`. Any role in the token is ignored.

### Alternative: Docker

`backend/Dockerfile` (python:3.12-slim, non-root) runs migrations and then uvicorn on `$PORT`:

```bash
docker build -t badminton-api backend
docker run --rm -p 8000:8000 --env-file backend/.env.production.local badminton-api
```

On Render choose Runtime Docker with root directory `backend` and the same env vars. The `.env.production.local` file is for local testing only and must not be committed (`.env.*` is git-ignored).

## 3. First deploy and migrations

1. Deploy on Render. The start command applies all Alembic migrations before serving. Watch the logs for `Running upgrade  -> f333d470133c, initial schema` on the first run and no errors afterwards.
2. Create the admin allowlist row, either of:
   - Set `ADMIN_BOOTSTRAP_USER_ID` and `ADMIN_BOOTSTRAP_EMAIL` on Render and redeploy; startup upserts the row.
   - Or open Render > Shell (or run locally with the production `DATABASE_URL` exported) from the `backend` directory:

```bash
python -m app.cli create-admin --auth-user-id <admin-uuid> --email <admin-email> --display-name "Club Admin"
python -m app.cli list-admins
```

`--auth-user-id` and `--email` are required, `--display-name` is optional. Other commands: `deactivate-admin --auth-user-id <uuid>`, and `seed-demo [--reset]` which loads demo data. Do not run `seed-demo` on the production database unless demo data is wanted; `--reset` wipes existing club data.

To run migrations manually from a workstation (needs the session pooler or direct string):

```bash
cd backend
DATABASE_URL='postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require' \
  .venv/bin/alembic upgrade head
```

## 4. Vercel (frontend)

1. Vercel > Add New > Project, import this repository, and set Root Directory to `frontend`. The framework preset is detected as Next.js; no `vercel.json` is needed. Build and output settings stay at their defaults.
2. Add environment variables for the Production environment (and Preview if wanted):

| Variable | Value | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `https://<render-service>.onrender.com/api/v1` | Include `/api/v1`. No trailing slash. |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<ref>.supabase.co` | Public. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | the anon / publishable key | Public. Never the service-role key. |
| `NEXT_PUBLIC_AUTH_MODE` | `supabase` | Production must not use `dev`. |

`NEXT_PUBLIC_*` values are inlined at build time. After changing one, redeploy.

3. Deploy, then copy the production URL (for example `https://your-app.vercel.app`).
4. Supabase > Authentication > URL Configuration: set Site URL to the Vercel URL and add it to Redirect URLs (also the custom domain, if any).

## 5. CORS

Set `CORS_ORIGINS` on Render to the exact Vercel origin (scheme and host, no path, no trailing slash). For several origins, comma-separate them:

```
CORS_ORIGINS=https://your-app.vercel.app,https://www.example.com
```

Redeploy or restart the Render service after changing it. Vercel preview URLs are different origins and are blocked unless listed.

## 6. Smoke tests

Replace `API` with `https://<render-service>.onrender.com`. On Render's free tier the first request after idle can take 30 to 60 seconds.

```bash
API=https://<render-service>.onrender.com

# Liveness and database connectivity: 200 {"status":"ok","database":"ok"}
curl -i $API/api/v1/health

# Public read routes: 200
curl -i $API/api/v1/players

# Admin routes without a token: 401
curl -i -X POST $API/api/v1/admin/players -H 'Content-Type: application/json' -d '{"display_name":"x"}'

# CORS preflight from the frontend origin: access-control-allow-origin must echo it
curl -i -X OPTIONS $API/api/v1/health \
  -H 'Origin: https://your-app.vercel.app' -H 'Access-Control-Request-Method: GET'

# Admin with a real token. Sign in with the anon key, then call an admin route: 200
TOKEN=$(curl -s -X POST "https://<ref>.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: <anon-key>" -H 'Content-Type: application/json' \
  -d '{"email":"<admin-email>","password":"<admin-password>"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -i -H "Authorization: Bearer $TOKEN" $API/api/v1/admin/me
```

Then in a browser: open the Vercel site, check the public pages load, sign in on the login page, add a player and a match, and confirm ratings update. A signed-in user who is not in `admin_users` must get 403 on admin routes.

## 7. Rollback and backups

Rollback of code:

- Render: Events or Deploys > pick the previous good deploy > Rollback. Vercel: Deployments > previous deployment > Promote to Production.
- Rolling back code does not roll back the schema. The start command only upgrades. If a bad migration must be reverted, from `backend` with the production `DATABASE_URL`: `alembic downgrade -1`, then redeploy the older code. Take a backup first. A downgrade of the initial migration drops all tables.
- Prefer forward fixes: add a new Alembic migration rather than editing an applied one.

Backups:

- Supabase Pro plans include daily backups and point-in-time recovery options. The free plan has no downloadable automatic backups, so take your own before risky changes (migrations, resets, data corrections).
- Manual backup (use the session pooler or direct string, with `pg_dump` 17 or newer to match the server):

```bash
pg_dump "postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require" \
  --format=custom --no-owner --file=badminton-$(date +%F).dump
```

- Restore into an empty database: `pg_restore --no-owner --clean --if-exists -d "<url>" badminton-YYYY-MM-DD.dump`.
- Rating history is rebuildable: the match log is the source of truth, and the admin correction/replay flow recomputes ratings from it. Still back up the whole database.

## 8. Verified on PostgreSQL

Phase 7 task P7-01 ran, against a throwaway PostgreSQL 18 cluster, `alembic upgrade head`, `downgrade base`, `upgrade head` and `alembic check` (no drift), `seed-demo --reset` (8 players, 34 matches, sum of rating changes 0), and the backend test suite with `TEST_DATABASE_URL`:

```bash
cd backend
TEST_DATABASE_URL='postgresql://user@localhost:5432/scratch' .venv/bin/pytest -q
```

Each test gets its own schema in that database, which is dropped afterwards. Use an empty, throwaway database, never production. Tests that build their own SQLite file (migration, CLI subprocess and auth module tests) always run on SQLite. When creating a local cluster make sure the database encoding is UTF8, as Supabase does.
