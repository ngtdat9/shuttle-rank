# Handoff: Shuttle Rank

**Date:** 2026-11-19
**Branch:** `main`
**Status:** Phases 0 to 7 are complete. No open defects. Production deployment is still pending the owner's credentials.

## Start here

- `docs/FINAL_REPORT.md`: what was built, how it was verified, known limitations.
- `docs/DEPLOYMENT.md`: how to go live on Supabase, Render and Vercel.
- `README.md`: local setup and commands.
- `CLAUDE.md` and `.claude/agents/`: the multi-agent workflow (D-021). The main Claude Code session is the orchestrator, and the specialists run on Sonnet.

## Remaining owner actions

1. Create the Supabase project and the admin user, then gather the URL, JWT secret or JWKS, and anon key.
2. Deploy the backend to Render (`render.yaml`) and set the `sync: false` env vars.
3. Deploy the frontend to Vercel with Root Directory set to `frontend`, and set the `NEXT_PUBLIC_*` vars.
4. Run the smoke tests in `docs/DEPLOYMENT.md`.

## Ideas for after v1 (out of scope, per `BUILD_PLAN.md` section 14)

Avatar uploads, CSV export, and an end-to-end test runner (Playwright) in CI.
