# API Contract (v1)

This is the contract between the backend and the frontend. FastAPI's OpenAPI output (`/docs`, `/openapi.json`) must match it. Pydantic schemas in `backend/app/schemas/`, this document, and `frontend/types/` must agree. Changes go through the orchestrator (see `docs/DECISIONS.md`).

## Conventions

- **Base path:** `/api/v1`. JSON request and response bodies.
- **IDs:** UUID strings.
- **Datetimes:** ISO 8601 in UTC with a `Z` or `+00:00` suffix, for example `2026-11-19T09:00:00Z`. **Dates** use `YYYY-MM-DD`.
- **Win rate:** a float from `0` to `1`, or `null` when the player has played 0 matches.
- **Pagination:** query `page` (default 1) and `page_size` (default 20, max 100). The response is a `Paginated<T>`:
  ```json
  { "items": [], "total": 0, "page": 1, "page_size": 20 }
  ```
- **Errors:** every error has this shape:
  ```json
  { "error": { "code": "not_found", "message": "Player not found", "details": null } }
  ```

  | Status | `code` | When |
  |---|---|---|
  | 401 | `unauthorized` | Missing, malformed, invalid, or expired token |
  | 403 | `forbidden` | Valid token but the user is not an active admin |
  | 404 | `not_found` | Entity does not exist (soft-deleted matches count as missing) |
  | 409 | `conflict` | Duplicate (player name, participant, award) or a state conflict |
  | 422 | `validation_error` | Request schema validation failed; `details` lists field errors |
  | 422 | `business_rule_violation` | Valid shape but breaks a rule (self-match, winner not a participant, inactive player, …) |
  | 429 | `rate_limited` | Too many failed admin auth attempts |

- **Unknown fields:** write request bodies reject unknown fields (`extra = forbid`), so a client can never send `current_rating`, `highest_rating`, or `rating_change`. No endpoint edits ratings directly.

## Authentication

- Public `GET` endpoints need no auth.
- Every `/admin/*` endpoint requires `Authorization: Bearer <access token>`.
- **Supabase mode** (`AUTH_MODE=supabase`): the backend verifies the Supabase JWT.
  - It uses HS256 with `SUPABASE_JWT_SECRET` if that is set. Otherwise it uses the project JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`.
  - It checks `exp` and `aud` (= `SUPABASE_JWT_AUDIENCE`, default `authenticated`).
  - It then requires an active `admin_users` row whose `auth_user_id` equals the token's `sub`. Roles or claims sent by the browser are ignored.
- **Dev mode** (`AUTH_MODE=dev`, only allowed when `APP_ENV` is not `production`): the bearer token must equal `DEV_ADMIN_TOKEN`. The actor id is `dev-admin`. The app refuses to start with `AUTH_MODE=dev` in production.
- Failed admin auth attempts are rate-limited per client IP: 20 per 5 minutes, then `429`.

## Shared schemas

```ts
PlayerSummary {
  id: string; display_name: string; avatar_url: string | null;
  current_rating: number; is_active: boolean
}

FormResult = "W" | "L"

PlayerStats {
  matches_played: number; wins: number; losses: number; win_rate: number | null;
  current_streak: { type: FormResult; count: number } | null;
  recent_form: FormResult[];          // up to 5, most recent first
  last_rating_change: number | null;  // change from the player's most recent rated match
  rating_change_30d: number;          // net change from matches in the last 30 days, 0 if none
}

RankingEntry {
  rank: number;                       // 1-based; ties share a rank (1, 2, 2, 4)
  player: PlayerSummary;
  rating: number; highest_rating: number;
  matches_played: number; wins: number; losses: number; win_rate: number | null;
  last_rating_change: number | null; rating_change_30d: number;
  recent_form: FormResult[];
}

RatingChange { player_id: string; old_rating: number; new_rating: number; rating_change: number }

Match {
  id: string;
  player_a: PlayerSummary; player_b: PlayerSummary;
  winner_id: string;
  match_date: string;                 // datetime
  status: "completed" | "canceled" | "disputed";
  tournament: { id: string; name: string } | null;
  game_scores: [number, number][] | null;   // per game, player_a score first
  notes: string | null;
  rating_changes: RatingChange[];     // empty unless the match was rated (completed)
  created_at: string; updated_at: string
}

PlayerMatch extends Match {           // a match from one player's perspective
  opponent: PlayerSummary;
  result: FormResult;
  rating_change: number | null;       // null if the match was not rated
}

Achievement {
  id: string; name: string; description: string; icon: string;   // lucide icon name
  criteria_type: string; criteria_value: number | null; is_active: boolean;
  awarded_count: number
}

PlayerAchievement { id: string; achievement: Achievement; awarded_at: string; notes: string | null }

AchievementAward { id: string; player: PlayerSummary; achievement: Achievement; awarded_at: string }

TournamentSummary {
  id: string; name: string; description: string | null;
  format: "single_elimination";
  status: "draft" | "in_progress" | "completed" | "canceled";
  start_date: string | null; end_date: string | null;
  participant_count: number;
  champion: PlayerSummary | null;
  created_at: string
}

BracketMatch {
  id: string; round: number; position: number;     // round 1 = first round; position 0-based
  player_a: PlayerSummary | null; player_b: PlayerSummary | null;
  seed_a: number | null; seed_b: number | null;
  winner_id: string | null;
  is_bye: boolean;
  status: "pending" | "ready" | "completed" | "bye";
  // pending: a slot is still empty; ready: both players known, no result yet
  match_id: string | null; match_date: string | null; game_scores: [number, number][] | null
}

Bracket {
  tournament_id: string;
  rounds: { round: number; name: string; matches: BracketMatch[] }[];  // [] if not generated
}
```

Round names count back from the final: `Final`, `Semifinals`, `Quarterfinals`, and `Round of 16` and so on for earlier rounds.

## Business rules the API enforces

- **Elo:** start 1500, K=32, divisor 400. `delta = floor(32 * (1 - E_winner) + 0.5)`. The winner gains `+delta` and the loser `-delta`. The calculation uses pre-match ratings, and only `completed`, non-deleted matches are rated.
- **Processing order:** matches are processed in order of (`match_date`, `created_at`, `id`).
- **Backdated changes trigger replay:** a new match dated before the latest rated match, or any correction, cancellation, or deletion, triggers a replay:
  1. Restore every player's rating from before the earliest affected match.
  2. Delete and rebuild the `rating_history` rows for that match and every later one.
  3. Recompute `current_rating` and `highest_rating`, then rebuild the monthly snapshots.

  All of this happens in one transaction, with an audit log entry.
- **Highest rating:** `highest_rating` is the maximum of 1500 and every `new_rating` the player has had.
- **No double processing:** a match is never processed twice. The unique constraint on `rating_history(match_id, player_id)` backs this up.
- **Monthly snapshots** are kept for every month from the first rated match's month through the current month (UTC). A player appears in a month once they have at least one rated match at or before the end of that month.
  - `rating` is the rating at month end.
  - `wins`, `losses`, `matches_played`, and `rating_change_during_month` count only that month.
  - Rank is by rating at month end. There is no monthly reset.
- **Deactivating a player** keeps all of their history. Inactive players are hidden from the default rankings and directory but remain visible in matches and profiles. They cannot be put in new matches or tournaments.

---

## Public endpoints

### `GET /health`
Returns `{ "status": "ok", "database": "ok" }`, or `503` with `"database": "error"` if the database check fails.

### `GET /dashboard`
```ts
{
  leader: RankingEntry | null;
  top_players: RankingEntry[];                 // top 5
  totals: { active_players: number; total_matches: number;   // completed, non-deleted
            matches_this_month: number; tournaments_completed: number };
  recent_matches: Match[];                     // 5 most recent completed
  rating_progression: { player: PlayerSummary;
                        points: { match_date: string | null; rating: number }[] }[];
                        // top 5 players; first point is { match_date: null, rating: 1500 }
  active_tournament: TournamentSummary | null; // in_progress first, else the latest draft
  recent_achievements: AchievementAward[];     // 5 most recent
  last_updated: string | null                  // match_date of the latest rated match
}
```

### `GET /rankings`
- **Query:** `include_inactive` (bool, default false); `sort` (`rank`|`rating`|`win_rate`|`wins`|`losses`|`matches_played`|`highest_rating`, default `rank`); `order` (`asc`|`desc`, default `asc` for `rank`, `desc` otherwise).
- **Response:** `{ items: RankingEntry[]; last_updated: string | null }`.
- **Ranking order:** rating desc, then wins desc, then display_name asc. Players with 0 matches are included.

### `GET /rankings/monthly`
- **Query:** `year`, `month` (optional; default the latest available month).
- **Response:**
  ```ts
  {
    available_months: { year: number; month: number }[];    // newest first
    year: number | null; month: number | null;
    items: { rank: number; player: PlayerSummary; rating: number;
             rank_change: number | null;   // vs previous month; positive = moved up; null if new
             wins: number; losses: number; matches_played: number;
             rating_change_during_month: number }[]
  }
  ```
- Returns `404` if the requested month has no snapshot. With no data at all, it returns empty arrays and null year and month.

### `GET /players`
- **Query:** `include_inactive` (default false), `search` (case-insensitive substring of display_name).
- **Response:** `{ items: PlayerListItem[] }`, ordered by rank and not paginated, since the club is small.
  ```ts
  PlayerListItem extends PlayerSummary {
    highest_rating: number; rank: number | null;   // null if inactive
    matches_played: number; wins: number; losses: number; win_rate: number | null
  }
  ```

### `GET /players/{id}`
Returns a `PlayerProfile` (inactive players included) or `404`.
```ts
PlayerProfile extends PlayerSummary {
  highest_rating: number; rank: number | null;
  stats: PlayerStats;
  created_at: string; updated_at: string
}
```

### `GET /players/{id}/matches`
- **Query:** `page`, `page_size`, `status` (default `completed`; `all` returns every non-deleted match).
- **Response:** `Paginated<PlayerMatch>`, ordered by `match_date` desc.

### `GET /players/{id}/rating-history`
Points are chronological, ascending.
```ts
{ player_id: string; starting_rating: 1500;
  points: { match_id: string; match_date: string; old_rating: number; new_rating: number;
            rating_change: number; opponent: PlayerSummary; result: FormResult }[] }
```

### `GET /players/{id}/monthly`
Returns `{ items: { year, month, rating, rank, wins, losses, matches_played, rating_change_during_month }[] }`, ascending by month.

### `GET /players/{id}/achievements`
Returns `{ items: PlayerAchievement[] }`, newest first.

### `GET /matches`
- **Query:**
  - `page`, `page_size`
  - `player_id`
  - `status` (`completed` default | `canceled` | `disputed` | `all`)
  - `tournament_id`
  - `date_from`, `date_to` (dates, inclusive, UTC)
  - `search` (case-insensitive substring of either player's name)
- **Response:** `Paginated<Match>`, ordered by `match_date` desc.

### `GET /matches/{id}`
Returns a `Match` or `404`. Soft-deleted matches return `404`.

### `GET /head-to-head/{player_a}/{player_b}`
Returns `422 business_rule_violation` if the two IDs are equal and `404` if either player is unknown. Only completed matches count.
```ts
{
  player_a: PlayerSummary; player_b: PlayerSummary;
  total_matches: number; player_a_wins: number; player_b_wins: number;
  player_a_win_rate: number | null; player_b_win_rate: number | null;
  current_streak: { player_id: string; count: number } | null;
  player_a_net_rating_change: number;     // sum of A's rating changes in these matches
  matches: Match[]                         // all encounters, newest first
}
```

### `GET /tournaments`
- **Query:** `status` (optional).
- **Response:** `{ items: TournamentSummary[] }`. In-progress tournaments come first, then by `start_date` desc and then `created_at` desc.

### `GET /tournaments/{id}`
Returns a `TournamentDetail` or `404`.
```ts
TournamentDetail extends TournamentSummary {
  participants: { player: PlayerSummary; seed: number | null; final_position: number | null }[];  // by seed
  bracket_generated: boolean;
  runner_up: PlayerSummary | null;
  updated_at: string
}
```

### `GET /tournaments/{id}/bracket`
Returns a `Bracket`, or `404` if the tournament doesn't exist.

### `GET /achievements`
- **Query:** `include_inactive` (default false).
- **Response:** `{ items: Achievement[] }`.

---

## Admin endpoints (all require admin auth)

Every write records an audit log entry: actor, action, entity, and before/after JSON.

### Session and overview
- `GET /admin/me` returns `{ id: string; email: string | null; display_name: string | null; auth_mode: "supabase" | "dev" }`.
- `GET /admin/stats` returns:
  ```ts
  { players_total, players_active, matches_total, matches_completed, matches_canceled,
    matches_disputed, tournaments_total, tournaments_in_progress, achievements_awarded: number;
    last_match_at: string | null }
  ```
- `GET /admin/audit-logs`: `page`, `page_size`, `entity_type`, `action`. Returns `Paginated<{ id, actor_id, action, entity_type, entity_id, before_data, after_data, created_at }>`, newest first.

Audit `action` values:
- Players: `player.create`, `player.update`, `player.deactivate`
- Matches: `match.create`, `match.update`, `match.correct`, `match.cancel`, `match.delete`
- Tournaments: `tournament.create`, `tournament.update`, `tournament.participants_add`, `tournament.participant_remove`, `tournament.bracket_generate`, `tournament.match_record`
- Achievements: `achievement.create`, `achievement.update`, `achievement.award`, `achievement.revoke`
- Rankings: `rankings.monthly_rebuild`

### Players
- **`GET /admin/players`** returns `{ items: PlayerListItem[] }` with all players, including inactive ones.
- **`POST /admin/players`** with body `{ display_name: string (trimmed, 1–50); avatar_url?: string | null }`.
  - Returns `201` with a `PlayerProfile`.
  - Returns `409` if the name already exists (case-insensitive).
- **`PATCH /admin/players/{id}`** with body `{ display_name?; avatar_url?; is_active? }`.
  - Returns a `PlayerProfile`.
  - Reactivating a player is allowed.
- **`DELETE /admin/players/{id}`** deactivates the player (`is_active=false`) and returns a `PlayerProfile`. It never hard-deletes.

### Matches
- **`GET /admin/matches`** is the same as public `GET /matches`, plus `include_deleted` (default false). `status` defaults to `all`.
- **`POST /admin/matches`** with body:
  ```ts
  { player_a_id; player_b_id; winner_id; match_date: datetime;   // not more than 1 day in the future
    status?: "completed" | "disputed";  // default completed
    game_scores?: [number, number][] | null; notes?: string | null }
  ```
  - Returns `201` with a `Match`.
  - Returns `422` if a player plays themselves, the winner isn't one of the two players, a player is inactive, or a player is unknown (unknown players return `422`, not `404`).
  - A backdated match triggers replay.
  - Tournament matches can't be created here.
- **`PATCH /admin/matches/{id}`** with body `{ notes?; game_scores? }`. This changes only details that don't affect ratings. Returns a `Match`.
- **`POST /admin/matches/{id}/correct`** with body:
  ```ts
  { player_a_id?; player_b_id?; winner_id?; match_date?; status?: "completed" | "disputed" | "canceled";
    reason: string (1–500) }
  ```
  - Returns a `Match`.
  - Replays from the earlier of the old and new date.
  - For tournament matches:
    - Players can't be changed.
    - The winner can change only if the next bracket match has no result yet. The bracket advancement is updated to match.
- **`POST /admin/matches/{id}/cancel`** with body `{ reason: string }`.
  - Sets the status to `canceled`, replays ratings, and returns a `Match`.
  - The same tournament rule applies: if the next bracket match has a result, it returns `422`. Otherwise the bracket slot goes back to `ready`.
- **`DELETE /admin/matches/{id}?reason=...`** soft-deletes the match (sets `deleted_at`), replays ratings, and returns `{ id: string; deleted: true }`. Tournament matches follow the same rule as cancellation.

### Tournaments
- **`GET /admin/tournaments`** is the same as public.
- **`POST /admin/tournaments`** with body `{ name (1–100); description?; start_date?; end_date? }` returns `201` with a `TournamentDetail` in status `draft`.
- **`PATCH /admin/tournaments/{id}`** with body `{ name?; description?; start_date?; end_date?; status?: "canceled" }`. A tournament can be canceled from `draft` or `in_progress`. Its rated matches stay rated.
- **`POST /admin/tournaments/{id}/participants`** with body `{ participants: { player_id: string; seed?: number | null }[] }`.
  - Only allowed in `draft`.
  - Returns `409` for a duplicate participant and `422` for an inactive or unknown player.
  - Returns a `TournamentDetail`.
- **`DELETE /admin/tournaments/{id}/participants/{player_id}`** is only allowed in `draft`. Returns a `TournamentDetail`.
- **`POST /admin/tournaments/{id}/generate-bracket`** with body `{ seeding?: "rating" | "manual" }` (default `rating`).
  - Requires at least 2 participants.
  - Allowed in `draft`, or in `in_progress` when no result has been recorded yet, which regenerates the bracket.
  - Seeding:
    - `rating` assigns seeds by current rating.
    - `manual` uses the participant seeds; any unseeded players go last, ordered by rating.
  - The bracket size is the next power of 2. Standard seed placement keeps seeds 1 and 2 apart until the final. Byes go to the top seeds and advance them automatically.
  - Sets the status to `in_progress` and returns a `Bracket`.
- **`POST /admin/tournaments/{id}/matches`** with body:
  ```ts
  { bracket_match_id; winner_id; match_date; game_scores?; notes? }
  ```
  - The bracket match must be `ready`, and the winner must be one of its two players.
  - The result is recorded as a normal rated match with `tournament_id` set, using the same Elo rules.
  - The winner advances to the next round.
  - When the final is recorded, the tournament becomes `completed` and final positions are set: champion 1, runner-up 2, semifinal losers 3, quarterfinal losers 5, and so on.
  - Returns `201` with `{ match: Match; bracket: Bracket }`.

### Achievements
- **`GET /admin/achievements`** returns `{ items: Achievement[] }`, including inactive achievements.
- **`POST /admin/achievements`** with body `{ name (1–80); description (1–300); icon?: string; criteria_type?: string; criteria_value?: number | null }` returns `201` with an `Achievement`. Returns `409` if the name is a duplicate.
- **`PATCH /admin/achievements/{id}`** accepts the same fields, all optional, plus `is_active`.
- **`GET /admin/player-achievements`** supports `page` and `page_size` and returns `Paginated<AchievementAward & { notes: string | null; awarded_by: string }>`.
- **`POST /admin/players/{id}/achievements`** with body `{ achievement_id; notes? }`.
  - Returns `201` with an `AchievementAward`.
  - Returns `409` if the player already has the award and `422` if the achievement is inactive.
- **`DELETE /admin/player-achievements/{id}`** revokes an award and returns `{ id: string; deleted: true }`.

### Rankings maintenance
- `POST /admin/rankings/monthly/rebuild` rebuilds all monthly snapshots and returns `{ months_rebuilt: number }`. This normally happens automatically.
