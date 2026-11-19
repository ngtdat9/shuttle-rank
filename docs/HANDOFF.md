# Handoff: Shuttle Rank

**Date:** 2026-11-19
**Branch:** `main`
**Status:** Phases 0 to 7 are complete. No open defects. **Deployed to production on 2026-11-19.**

## Live

| Part | Where |
|---|---|
| Site | https://shuttle-rank-club.vercel.app (Vercel project `shuttle-rank`, root `frontend`) |
| API | https://shuttle-rank-api.onrender.com (Render `shuttle-rank-api`, Singapore, free) |
| Database and auth | Supabase project `eixqinyqwfjzhjxyirhg` (ap-southeast-1); logins verified via JWKS (ES256), so no JWT secret is set |
| Admin | The allowlisted Supabase user, bootstrapped through `ADMIN_BOOTSTRAP_*` on Render |

Render was created through its API, so the build and start commands begin with `cd backend &&` instead of using `rootDir`. Pushing to `main` redeploys both the site and the API.

## Start here

- `docs/FINAL_REPORT.md`: what was built, how it was verified, known limitations.
- `docs/DEPLOYMENT.md`: how to go live on Supabase, Render and Vercel.
- `README.md`: local setup and commands.
- `CLAUDE.md` and `.claude/agents/`: the multi-agent workflow (D-021). The main Claude Code session is the orchestrator, and the specialists run on Sonnet.

## Remaining owner actions

1. Turn off public sign-ups in Supabase Auth, if not done yet.
2. Sign in at `/admin/login` and add the players.
3. Optionally, add an uptime pinger on `/api/v1/health` to avoid Render cold starts.

## Ideas for after v1 (out of scope, per `BUILD_PLAN.md` section 14)

Avatar uploads, CSV export, and an end-to-end test runner (Playwright) in CI.
