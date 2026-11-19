# Shuttle Rank — requirements

Public Elo ladder for a club of 6–10 friends. Men's singles only. One admin. Anyone with the link can read. The product should feel like a small sports analytics site: rankings and matches first.

**Sources.** `docs/BUILD_PLAN.md`, `docs/API.md`, and the owner brief (app name, page list, desktop-first, visual direction). Payloads, status codes, and validation limits live in `docs/API.md`. This document is the behaviour a visitor or admin can see. Tests should satisfy both. If a payload and a sentence here ever disagree, `docs/API.md` wins and this file should be updated in the same change.

**Build order.** Unmarked criteria belong to the first usable version (`BUILD_PLAN.md` §14–15). Criteria marked **P6** ship with tournaments, monthly snapshots, and achievements. Nav entries for those areas can exist earlier; their empty states are valid.

**Defaults.** Section 14 records choices the plan left open. They are requirements until the owner changes them.

---

## 1. Visitors, auth, and security

| ID | Acceptance criterion |
|---|---|
| R-SEC-01 | Dashboard, leaderboard, monthly board, players, profiles, matches, match detail, head-to-head, and tournaments load with no session. |
| R-SEC-02 | There is no registration screen and no public sign-up call. |
| R-SEC-03 | Admin signs in at `/admin/login` with email and password. A failed sign-in does not reveal whether the email exists. |
| R-SEC-04 | Admin API calls send the Supabase access token as `Authorization: Bearer`. The backend verifies the JWT and requires an active `admin_users` row for `sub`. A role sent by the browser is ignored. |
| R-SEC-05 | Anonymous callers and signed-in non-admins receive 401 or 403 on every `/admin/*` route, including calls made outside the UI. |
| R-SEC-06 | `AUTH_MODE=dev` is refused when `APP_ENV=production`. Outside production, the dev token is `DEV_ADMIN_TOKEN` and the actor id is `dev-admin`. |
| R-SEC-07 | Failed admin auth is rate-limited to 20 attempts per 5 minutes per IP and then returns 429. |
| R-SEC-08 | The service-role key, JWT secret, and database URL never appear in `NEXT_PUBLIC_*` or the client bundle. Only the public Supabase URL and anon key may. |
| R-SEC-09 | Write bodies reject unknown fields. No request can set `current_rating`, `highest_rating`, or `rating_change`. |
| R-SEC-10 | The public header has no Admin item. The footer links to `/admin/login`. Public pages render no create, edit, correct, cancel, or delete controls, including when an admin token is present in the browser. |

---

## 2. Elo

Ratings are integers. The UI never shows a decimal Elo.

| ID | Acceptance criterion |
|---|---|
| R-ELO-01 | A new player starts at 1500 current and 1500 highest. K is 32 and the divisor is 400. No screen can change K, the divisor, or a starting rating. |
| R-ELO-02 | Expected score is `1 / (1 + 10^((R_opponent − R_player) / 400))`. `delta = floor(32 * (1 − E_winner) + 0.5)`. The winner receives `+delta` and the loser `−delta`. The two changes sum to 0. |
| R-ELO-03 | Two players at 1500 produce +16 and −16. |
| R-ELO-04 | The delta uses both pre-match ratings. Game scores, notes, and margin do not change it. A tournament match uses the same delta, with no bonus. |
| R-ELO-05 | Only a `completed`, non-deleted match changes ratings. `canceled` and `disputed` matches leave ratings untouched. |
| R-ELO-06 | A match is rated at most once. It writes two `rating_history` rows (one per player) with old rating, new rating, and signed change, unique on `(match_id, player_id)`. |
| R-ELO-07 | Rated matches are ordered by `match_date`, then `created_at`, then `id`. |
| R-ELO-08 | A backdated create, a correction, a cancellation, or a deletion replays in one transaction from the earliest affected match: rebuild later history, recompute current rating, set highest to the max of 1500 and every remaining `new_rating` (the peak may fall), rebuild monthly snapshots, and write an audit entry. The result equals a full recalculation from an empty history. |
| R-ELO-09 | No screen contains an input for a rating or a delta. After a write, the UI refetches. It does not patch a rating in memory. |

---

## 3. Players

| ID | Acceptance criterion |
|---|---|
| R-PL-01 | Create asks for `display_name` (trimmed, 1–50 characters, unique case-insensitively) and an optional avatar URL. There is no file upload. The created player is active and rated 1500. |
| R-PL-02 | Edit can change the name, the avatar URL, and `is_active`. A duplicate name returns 409. Ratings stay read-only on the form. |
| R-PL-03 | Deactivate (`DELETE /admin/players/{id}`) sets `is_active` false and keeps every match and rating row. The player leaves the default leaderboard and directory. Their profile URL still loads. |
| R-PL-04 | Reactivate is allowed (`PATCH` with `is_active: true`) and does not change the rating. |
| R-PL-05 | An inactive player cannot be added to a new club match or a tournament. A 422 explains that. Past matches still show their name. |
| R-PL-06 | Create, edit, deactivate, and reactivate each write an audit row (`player.create`, `player.update`, `player.deactivate`). |

---

## 4. Matches

`match_date` is a UTC datetime. The admin may not set it more than one day in the future. The UI shows it in the viewer's local timezone, date and time, no seconds.

| ID | Acceptance criterion |
|---|---|
| R-MA-01 | Recording a club match requires two different active players and a winner who is one of them. Default status is `completed`. Status may instead be `disputed` at creation, in which case no rating changes. |
| R-MA-02 | Game scores are optional pairs of integers, player A first, at most five games, each side 0–99. Notes are optional, at most 500 characters. Neither changes Elo. |
| R-MA-03 | The API rejects a self-match, a winner outside the pair, an inactive player, and an unknown player. The form shows the error and does not close. |
| R-MA-04 | `POST /admin/matches` cannot create a tournament match. Tournament results are recorded from a bracket slot (**P6**). |
| R-MA-05 | Notes and scores can be patched later with no replay. Date, players, winner, and status go through correct, cancel, or delete. |
| R-MA-06 | Correct requires a reason of 1–500 characters and a confirmation dialog. It replays from the earlier of the old and new dates. On a tournament match the players stay fixed, and the winner can change only while the next slot has no result; otherwise the dialog shows the 422 and stays open. |
| R-MA-07 | Cancel requires a reason and a confirmation. Status becomes `canceled`, the row stays on the public list when that filter is on, and later ratings replay. The same next-slot rule applies to tournament matches. |
| R-MA-08 | Delete requires a reason and a confirmation. The match disappears from public pages (detail returns 404), ratings replay, and the audit row keeps the previous result. There is no restore. Admin match list can include deleted rows; those rows have no further write actions. |
| R-MA-09 | Moving a match between `completed`, `disputed`, and `canceled` goes through correct (or cancel) so the replay cannot be skipped. |
| R-MA-10 | The public list defaults to `completed`, 20 per page, newest `match_date` first. Filters: player, status (`completed`, `canceled`, `disputed`, `all`), one tournament, inclusive UTC `date_from` / `date_to`, and a case-insensitive name search. |
| R-MA-11 | Match detail shows both players (A named as A), the winner, local date and time, status, each player's old → new and signed change, or the sentence "No rating change" when `rating_changes` is empty, plus tournament link, scores, and notes when present. |

---

## 5. Leaderboard and monthly standings

Win rate in the API is a float from 0 to 1, or `null` when the player has no completed match. The UI prints one decimal percent (`0.5` → `50.0%`). `null` is an em dash. W–L counts completed matches only and is printed with an en dash (`12–7`).

`recent_form` is at most five `W` or `L` values, **most recent first**. The UI paints the chips oldest on the left and newest on the right.

| ID | Acceptance criterion |
|---|---|
| R-LB-01 | Default order is rating desc, then wins desc, then `display_name` asc. Active players with no matches appear at 1500 with `0–0`. |
| R-LB-02 | The rank number is the API `rank`. Equal ratings share a rank and the next rank skips (`1, 2, 2, 4`). Sorting the table does not renumber ranks. The UI pads ranks below 10 to two digits (`01`). |
| R-LB-03 | Columns: rank, player, Elo, W–L, win rate, last-match change, form, highest rating. Inactive players are absent. There is no public "show inactive" control. |
| R-LB-04 | Sort keys: `rank`, `rating`, `win_rate`, `wins`, `losses`, `matches_played`, `highest_rating`, with the contract's default direction. A name filter runs in the browser on the returned list and keeps each row's real rank. |
| R-LB-05 | A row opens `/players/{id}`. The page links to `/leaderboard/monthly`. |
| R-MO-01 | **P6.** `/leaderboard/monthly` lists `available_months`, newest first, and defaults to the latest. A month the API does not know is not offered. The page never resets a rating. |
| R-MO-02 | **P6.** Each row shows position, rank change versus the previous month, player, rating at month end, in-month W–L, and `rating_change_during_month`. Positive `rank_change` means the player moved up. `null` rank change is "New". `0` is an em dash. |
| R-MO-03 | **P6.** The current UTC month is labeled "in progress". A player is listed once they have any rated match on or before that month's end, including a `0–0` month. Deactivating someone later does not remove them from a past month. |
| R-MO-04 | **P6.** Copy on the page states that ratings carry over and the table is the standing at the end of that month. |

`rating_change_30d` is shown on the player profile only, not as a leaderboard column.

---

## 6. Directory, profile, and head-to-head

| ID | Acceptance criterion |
|---|---|
| R-PR-01 | `/players` lists active players in rank order: rank, name, avatar or initials, Elo, highest, W–L, win rate. Search hits `display_name`, case-insensitive. |
| R-PR-02 | `/players/{id}` loads for an inactive player. It shows name, avatar or initials, "Inactive" when `rank` is null, otherwise the rank, Elo, highest, W–L, win rate, last-match change, 30-day change, current streak when `stats.current_streak` is set, and form. |
| R-PR-03 | The profile chart plots `starting_rating` (1500) and then each `/rating-history` point in order. The tooltip uses that point's date, opponent, result, new rating, and `rating_change`. The client does not invent points. |
| R-PR-04 | The profile lists that player's matches, newest first, default `completed`, with opponent, result, delta, date, a link to the match, and a link to head-to-head for that opponent. Achievements (**P6**) and the month-by-month table (**P6**, from `/players/{id}/monthly`) sit on the same page. |
| R-PR-05 | An unknown player id shows the not-found state, not an empty profile. |
| R-H2H-01 | `/head-to-head?a={id}&b={id}` is shareable. The pickers list every player, including inactive, and mark inactive ones. The same id in both slots is blocked before the request. |
| R-H2H-02 | The page shows total completed matches, wins and win rate for each side, `player_a_net_rating_change`, and the streak sentence when `current_streak` is set. Encounters are the returned `matches`, newest first, including tournament matches. Swapping `a` and `b` swaps the sides. |
| R-H2H-03 | Zero completed meetings shows the players and the sentence "No completed matches between these two." Unknown ids show not-found. |

There is no separate "all rivals" payload. Head-to-head shortcuts are the per-match links in R-PR-04.

---

## 7. Tournaments (P6)

Single elimination only. The client renders `GET /tournaments/{id}/bracket` in round and `position` order. It does not re-seed.

| ID | Acceptance criterion |
|---|---|
| R-TN-01 | The list shows name, status, start date, end date when set, participant count, and champion when `champion` is set. In-progress tournaments come first. |
| R-TN-02 | Detail shows description, participants with seed and final position, champion, runner-up, and the bracket after it exists. An ungenerated bracket says the bracket has not been generated. |
| R-TN-03 | Generate requires at least two active participants. Size is the next power of two. Byes go to the top seeds, write no match, and change no rating. Seeds 1 and 2 can meet only in the final. |
| R-TN-04 | Seeding is `rating` (current Elo) or `manual` (assigned seeds, unseeded players last by Elo). Generate is allowed in `draft`, and again while `in_progress` only when no result has been recorded. |
| R-TN-05 | A result can be recorded only on a `ready` slot. The winner must be one of the two players. The match is a normal rated match with `tournament_id` set, and the winner advances. Recording the final sets status `completed`, champion position 1, runner-up 2, semifinal losers 3, quarterfinal losers 5, and the same skip for earlier rounds. |
| R-TN-06 | Participants can be added or removed only in `draft`. Inactive players are rejected. Cancel is allowed from `draft` or `in_progress` only. Matches already rated stay rated and stay linked. |
| R-TN-07 | The public bracket uses the payload's round `name` as the column title. A bye shows the advancer and the label BYE. A `pending` slot shows Waiting. A completed slot links to `/matches/{match_id}`. The public page has no control that records a result. |
| R-TN-08 | Final-position labels: 1 Champion, 2 Runner-up, 3 Semifinals, 5 Quarterfinals, 9 Round of 16. Any other number is shown as that place. |

---

## 8. Achievements (P6)

| ID | Acceptance criterion |
|---|---|
| R-AC-01 | Admin can create and edit a definition: name 1–80, description 1–300, lucide `icon` name, optional `criteria_type` and `criteria_value`, and `is_active`. A duplicate name returns 409. Criteria text is stored and shown in admin only. Nothing reads those fields to award a badge. |
| R-AC-02 | Awarding is a manual action, at most once per player per achievement. A repeat returns 409. An inactive definition returns 422. Revoke removes that award. Award and revoke write `achievement.award` and `achievement.revoke`. |
| R-AC-03 | A profile and the dashboard show the badge name, icon, player, and awarded date. An unknown icon name renders the `Award` icon. Notes show on the profile when present. |

---

## 9. Dashboard

Data comes from `GET /dashboard`. The client does not assemble ratings by replaying matches.

| ID | Acceptance criterion |
|---|---|
| R-DB-01 | The page shows, in order: club hero, leader card, Elo chart, top-five leaderboard, five recent completed matches, the active-or-draft tournament card, five recent awards. |
| R-DB-02 | Hero figures are `totals.active_players`, `totals.total_matches` (completed, non-deleted), and `totals.matches_this_month`. The latest line uses `recent_matches[0]` when it exists. With no players, every region uses its empty state and the page shows no made-up player or rating. |
| R-DB-03 | The leader card is `leader` (name, rank, Elo, W–L, win rate, highest, last change, form) and links to that profile. `leader: null` shows "No players yet." |
| R-DB-04 | The chart plots `rating_progression` (up to five players). The first point is `{ match_date: null, rating: 1500 }`. The tooltip shows the series name, the date, and the rating on that point. A legend can hide a series. |
| R-DB-05 | The tournament card is `active_tournament`: an in-progress event if one exists, otherwise the latest draft. It also shows `totals.tournaments_completed`. `null` shows "No tournament in progress" and a link to `/tournaments`. It does not substitute the most recent completed event. |
| R-DB-06 | Recent awards are `recent_achievements` (at most five). Recent matches are `recent_matches` (at most five, completed). `last_updated` is shown as the local time of the latest rated match when it is non-null. |

---

## 10. Admin

Admin routes use a separate shell (lime "Admin" chip, link back to the public site). Unauthenticated visits redirect to `/admin/login`. `/admin` redirects to `/admin/dashboard`.

| ID | Acceptance criterion |
|---|---|
| R-AD-01 | The overview shows `GET /admin/stats` (players total and active, matches by status, tournaments total and in progress, achievements awarded, last match time) and the ten newest audit rows, plus links to players, matches, tournaments, achievements, and the audit log. |
| R-AD-02 | Player admin lists every player, including inactive. The admin can create, edit, deactivate, reactivate, and open the public profile. The form shows Elo, highest, and W–L as text, never as inputs. |
| R-AD-03 | Match admin lists matches with `status=all` by default and can include deleted rows. The admin can record, patch notes and scores, correct, cancel, and delete. Record, correct, cancel, and delete each open a confirmation. Correct, cancel, and delete require a reason. |
| R-AD-04 | **P6.** Tournament admin can create (`draft`), edit name, description, and dates, cancel when the contract allows, add and remove participants only in draft, generate or regenerate the bracket, and record a `ready` slot. |
| R-AD-05 | **P6.** Achievement admin can create, edit, deactivate a definition, award, and revoke. Award asks for a player, an active definition, and optional notes. |
| R-AD-06 | `/admin/audit-log` is newest first, paged, and filters by `entity_type` and `action`. A row shows actor, action, entity type, entity id, and local time. Expanding it shows `before_data` and `after_data`. |
| R-AD-07 | A failed write leaves the dialog open and shows `error.message` (and field `details` on `validation_error`). The UI does not show success until the request succeeds. |
| R-AD-08 | The signed-in admin's email from `GET /admin/me` is visible in the admin header. `auth_mode: "dev"` shows a visible "Dev auth" chip so a stub session cannot be mistaken for production. |

Dialog copy and which actions need a reason are specified in `docs/ux/pages.md`.

---

## 11. Cross-cutting UI

| ID | Acceptance criterion |
|---|---|
| R-UX-01 | Every data region has a loading skeleton, an empty sentence, and an error state with Retry. Detail pages for an unknown id have a not-found state with a link back to the list. |
| R-UX-02 | A positive change is lime with a plus sign. A negative change is coral with a minus sign (U+2212). Zero is secondary text `0`. Null is an em dash. The sign is present in the text, not only in the color. |
| R-UX-03 | Stored instants are UTC. The UI formats them in the viewer's locale, with a short month and no seconds. Date filters send `YYYY-MM-DD` as the contract's UTC dates. The filter control's label includes "UTC". |
| R-UX-04 | Layouts are designed for a 1280px desktop first and remain usable at 375px width. Desktop and mobile both pass for every page in `docs/ux/pages.md`. |
| R-UX-05 | These routes are public and shareable: `/`, `/leaderboard`, `/leaderboard/monthly?year=&month=`, `/players`, `/players/{id}`, `/matches`, `/matches/{id}`, `/head-to-head?a=&b=`, `/tournaments`, `/tournaments/{id}`. |

Visual rules, breakpoints, and component anatomy are in `docs/ux/design-system.md`.

---

## 12. Out of scope

- BWF points, score-margin Elo, doubles, women's, or mixed.
- Public accounts, comments, notifications, and email digests.
- A screen to edit K, reset ratings, or type an Elo.
- Avatar file upload and CSV export.
- A generator that pairs the weekly matches. The admin enters the pairing the group already played.
- Evaluating `criteria_type` / `criteria_value` into automatic awards.
- Restoring a soft-deleted match, or hard-deleting a player who has history.
- Managing the admin allowlist inside the app. The second admin, if ever needed, is added in data, not in a UI.
- Live, point-by-point scoring.
- A public catalogue page of achievement definitions.

---

## 13. Data the UI depends on

These are already the contract in `docs/API.md`. Dropping them breaks a page above.

- **Dashboard:** `leader`, `top_players` (5), `totals` (active players, completed matches, matches this month, tournaments completed), `recent_matches` (5 completed), `rating_progression` for the top 5 with a leading 1500 point, `active_tournament` (in progress, else latest draft), `recent_achievements` (5), `last_updated`.
- **Ranking row:** shared `rank`, `highest_rating`, wins, losses, `win_rate`, `last_rating_change`, `recent_form` (newest first), `rating_change_30d`.
- **Monthly row:** `rank`, `rank_change` (positive = moved up), in-month wins and losses, `rating_change_during_month`, `available_months`.
- **Head-to-head:** both win counts and rates, `current_streak`, `player_a_net_rating_change`, full completed `matches` newest first.
- **Bracket slot:** `round`, `name`, `position`, seeds, players, `is_bye`, `status` (`pending` | `ready` | `completed` | `bye`), `match_id`.
- **Tournament:** `champion`, `runner_up`, `final_position`, `bracket_generated`.
- **Admin:** `GET /admin/stats`, `GET /admin/me`, paginated audit rows with `before_data` / `after_data`, and a required `reason` on correct, cancel, and delete.

Not in the contract, and not required for these pages:

- A filter for "club matches only" (`tournament_id` filters to one event). The match page does not offer that filter.
- Opponent and delta on dashboard chart points. The dashboard tooltip stays date + rating. The profile chart carries the richer history.
- A rival index on the profile. Shortcuts sit on each match row.
- Undelete.
- A completed-tournament fallback inside `active_tournament`.

---

## 14. Open questions — defaults in force

| ID | Question | Default this spec uses |
|---|---|---|
| OQ-01 | How should form be read? | Payload is newest-first. Chips are drawn oldest on the left. |
| OQ-02 | Where do 30-day change and streak go? | Player profile and head-to-head (streak). Not the leaderboard columns. |
| OQ-03 | Can the public board include inactive players? | No toggle. Inactive people remain on profiles, matches, monthly history, and the head-to-head pickers. |
| OQ-04 | What if nothing is in progress or draft? | The dashboard card is empty and links to the tournament list. It does not feature the last champion. |
| OQ-05 | Is delete a hard delete? | No. Soft delete, hidden from the public, replay runs, audit keeps the previous result, no restore control. |
| OQ-06 | Do achievement criteria auto-award? | No. Admin awards and revokes by hand. Criteria fields are notes. |
| OQ-07 | How many game-score rows? | The form allows up to five games, each side an integer 0–99. The contract does not state a cap; this is the UI limit. |
| OQ-08 | Notes length? | 500 characters in the form. Correct, cancel, and delete reasons stay 1–500 as in the contract. |
| OQ-09 | Desktop-first or mobile-first? | Design the 1280px layout first (owner brief). Every page must still work at 375px (`BUILD_PLAN.md` §9). |
| OQ-10 | Who is the leader when Elo is tied? | Both share the rank number. Row order is wins, then name. The dashboard `leader` card is the first player in that order, so the chip can read 01 while someone else also has rank 1. |
| OQ-11 | Should admin expose "rebuild monthly snapshots"? | No button. Replay rebuilds them. The maintenance endpoint stays out of the UI. |
| OQ-12 | Amber for disputed had no hex. | `#E8B84A` text on the dark surfaces. See `docs/ux/design-system.md`. |
