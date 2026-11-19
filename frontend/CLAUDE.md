# Frontend rules

## Structure
- Next.js App Router in `frontend/app/`. Public routes: `/`, `/leaderboard`, `/players`, `/players/[id]`, `/matches`, `/head-to-head`, `/tournaments`, `/tournaments/[id]`. Admin routes under `/admin/` (`login`, `dashboard`, `players`, `matches`, `tournaments`, `achievements`).
- Reusable UI in `frontend/components/`, hooks in `frontend/hooks/`, the API client and helpers in `frontend/lib/`, contract types in `frontend/types/`.
- TypeScript strict mode. No `any` for API data.

## Data and API
- The backend is the source of truth. Never calculate or adjust Elo ratings, ranks, or stats in the browser; render API values.
- All requests go through the single typed client in `frontend/lib/` using `NEXT_PUBLIC_API_BASE_URL`.
- Types in `frontend/types/` must match `docs/API.md`. Do not invent fields. If something is missing, report a contract gap.
- No hardcoded or mock data once a page is integrated with the API.

## Auth and security
- Admin sign-in uses Supabase Auth email/password. Send the access token as `Authorization: Bearer <token>` on admin requests. No public sign-up.
- Guard admin routes in navigation, but treat the backend as the only real enforcement.
- Only public config in `NEXT_PUBLIC_*` (API base URL, Supabase URL, anon key). Never the service-role key or any secret.

## UI
- Mobile-first and responsive. Leaderboard is easy to scan; rating changes have clear positive/negative indicators.
- Tailwind CSS + shadcn/ui. Recharts for rating progression.
- Every data view has loading, empty, and error states.
- Confirm before destructive or rating-affecting admin actions (record, correct, or cancel a match; deactivate a player).
- Accessible: labelled controls, keyboard navigation, sufficient contrast.

## Checks
- Type-check, lint, and build must pass before a task is reported done.
