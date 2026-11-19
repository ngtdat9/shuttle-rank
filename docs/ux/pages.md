# Shuttle Rank — page specs

Read `docs/ux/design-system.md` for color, type, tables, charts, chips, and dialogs. Read `docs/REQUIREMENTS.md` for behaviour. Field names below match `docs/API.md`.

Public pages show no write actions. Admin pages use the admin shell.

## Confirmations

Rating-affecting and destructive actions use the dialog in the design system. The API error stays inside the dialog.

| Action | Title | Body must name | Reason | Confirm label |
|---|---|---|---|---|
| Record club or bracket result | Record this result? | Both players and the winner | No | Record result |
| Correct | Replay ratings? | Both players. "Every later match is recalculated." | Yes, 1–500 | Replay ratings |
| Cancel match | Cancel this match? | Both players. "It stops affecting Elo. Later matches are recalculated." | Yes | Cancel match |
| Delete match | Delete this match? | Both players. "It leaves the public site. Ratings are recalculated. The audit log keeps the old result. This cannot be undone here." | Yes | Delete match |
| Deactivate | Deactivate {name}? | "They leave the leaderboard. Their matches stay." | No | Deactivate |
| Reactivate | Return {name} to the board? | "Their rating stays {current_rating}." | No | Reactivate |
| Generate bracket | Generate the bracket? | Player count and seeding mode. "Byes advance with no Elo change." | No | Generate |
| Regenerate | Replace the bracket? | "Only available because no result has been recorded." | No | Replace bracket |
| Cancel tournament | Cancel this tournament? | "Matches already played keep their ratings." | No | Cancel tournament |
| Award | Award {badge} to {name}? | — | No (notes optional) | Award |
| Revoke | Revoke {badge} from {name}? | — | No | Revoke |

Record, generate, and award use the lime confirm button. The other rows use the coral button. Initial focus is always Cancel. Enter never confirms.

---

## Public shell

**Who.** A visitor with the link.

**Header.** Wordmark "Shuttle Rank", section links, search (design system). Footer: one line "Men's singles · Elo" and a text link "Admin".

**Desktop order of links.** Dashboard, Leaderboard, Players, Matches, Head-to-head, Tournaments.

---

## Dashboard `/`

**Purpose.** Show who leads, how the ratings are moving, and what was just played.

**Desktop (≥1024), 12 columns.**

1. **Hero, span 7.** Eyebrow "Club". Title "Shuttle Rank". Line "Men's singles". If `recent_matches[0]` exists: "{winner} beat {loser}", the local date, and each signed delta from `rating_changes`. Else: "No completed matches yet." Bottom strip, three stats: `totals.active_players` / "Players", `totals.total_matches` / "Matches", `totals.matches_this_month` / "This month". If `last_updated` is set, muted "Updated {local datetime}".
2. **Leader card, span 5.** From `leader`. Chips: "Leader", rank `01`, and form chips when `recent_form` is not empty. Name. Display Elo (56px) with label "Elo". Then W–L, win rate, "Highest {highest_rating}", last delta. Initials or avatar. Lime button "View profile" → `/players/{id}`.
3. **Chart, span 5.** Title "Elo rating progression". Series from `rating_progression`. Caption "From the 1500 start."
4. **Leaderboard preview, span 7.** Title "Club leaderboard". Text button "View all" → `/leaderboard`. Table of `top_players`: rank, player, Elo, W–L, win rate, last delta. Row → profile.
5. **Recent matches, span 7.** Title "Recent matches". Up to five: local date, both names, winner in text color, loser muted, both deltas, tournament name when set. Row → `/matches/{id}`. Text button "All matches".
6. **Right stack, span 5.** Tournament card, then achievements card, gap 20.

**Tournament card.** From `active_tournament`: status chip, name, start date, "{participant_count} players", link to the detail. Draft copy: "Not started". In progress: "In progress". Muted line "{totals.tournaments_completed} completed". `null`: "No tournament in progress", the same completed count, and a link "All tournaments".

**Achievements card.** Title "Recent achievements". Up to five: icon, achievement name, player name, local date. Row → that player's profile.

**Below 1024.** One column: hero, leader card, chart, leaderboard preview, recent matches, tournament, achievements.

**Empty.** No players: hero counts are 0, 0, 0; leader card "No players yet."; chart "Ratings show up after the first completed match."; table "No players yet."; matches "No completed matches yet."

**Loading.** A skeleton for each of the six regions. **Error.** One error card for the whole page if `GET /dashboard` fails, with Retry.

---

## Leaderboard `/leaderboard`

**Purpose.** Scan the club order.

**Desktop.** Title "Leaderboard". On the same row: name filter (client-side), sort select, text link "Monthly view" → `/leaderboard/monthly`. Table of every returned active player.

**Columns.** Rank, player (avatar, name), Elo, W–L, win rate, last delta, form, highest. Rank is the payload rank, including shared ranks. Header does not renumber.

**Sort select.** Rank, Elo, Win rate, Wins, Losses, Matches, Highest. Default Rank. Changing sort refetches, then reapplies the name filter.

**Mobile.** Title, monthly link, filter, sort select, then one card per player (design-system card pattern).

**Row** → `/players/{id}`.

**States.** Loading: eight skeleton rows. Empty club: "No active players yet." Filter miss: "No players match “{query}”." Error: "Couldn't load the leaderboard." Retry.

---

## Monthly leaderboard `/leaderboard/monthly` (P6)

**Purpose.** Standings at the end of a month. Ratings are not reset.

**Desktop.** Title "Monthly leaderboard". Sentence under it: "Ratings carry over. This is the standing at the end of the month." Month select from `available_months`, newest first, labels "Nov 2026". The current UTC month gets the suffix "· in progress". Shareable query `?year=&month=`. Text link "Current leaderboard".

**Columns.** Position, move, player, rating, W–L, month delta (`rating_change_during_month`).

**Move column.** Positive: lime `▲{n}` ("up {n}" for the accessible name). Negative: coral `▼{n}`. Zero: em dash. `null`: "New".

**Mobile.** Same stack: title, sentence, month select, cards.

**States.** No months: "No completed matches yet." Loading skeletons. Error with Retry. The picker never offers a month that would 404.

---

## Players `/players`

**Purpose.** Find a person and open their profile.

**Desktop.** Title "Players". Search hits `GET /players?search=`. Grid of cards, three columns from 1024px, two from 768px. Card: avatar or initials, rank chip, name, Elo (28px), W–L and win rate, muted "Highest {n}". Whole card → profile.

**Mobile.** One column.

**States.** Loading: six skeleton cards. Empty: "No active players yet." No search hit: "No players match “{query}”." Error with Retry.

---

## Player profile `/players/[id]`

**Purpose.** One player's rating, record, history, and a way into head-to-head.

**Desktop.**

1. **Header card, full width.** Avatar or initials, name, rank chip or "Inactive", Elo, highest, W–L, win rate, last delta, muted "Last 30 days {rating_change_30d}", streak chip when `stats.current_streak` is set ("3 wins" / "2 losses"), form chips.
2. **Chart, span 7.** "Elo rating progression" from `/players/{id}/rating-history`. Prepend the 1500 start. Tooltip uses opponent, result, new rating, and `rating_change`.
3. **Side column, span 5.** Achievements (**P6**): icon, name, local date, notes if any. Empty: "No achievements yet."
4. **Matches, full width.** Default completed. Each row: date, opponent, W or L, delta, "Match" link, "Compare" link → `/head-to-head?a={this}&b={opponent}`. Pager when `total` exceeds `page_size`.
5. **By month, full width (P6).** From `/players/{id}/monthly`, newest at the bottom (payload is ascending). Columns: month, rank, rating, W–L, month delta. Empty: "No monthly record yet."

**Below 1024.** Stack header, chart, achievements, matches, by month.

**States.** Loading skeletons per region. A failed sub-request errors that region only; the header can still show. Unknown id: "This player isn't on Shuttle Rank." Link to `/players`. Chart with only the 1500 point: draw that point and caption "No completed matches yet. Rating is the 1500 start."

---

## Match history `/matches`

**Purpose.** Find a completed match, or inspect canceled and disputed ones.

**Filters, one wrapping row.** Name search, status select (Completed default, Canceled, Disputed, All), tournament select populated from `GET /tournaments` plus "Any tournament", date from, date to. Date labels read "From (UTC)" and "To (UTC)". "Clear" resets to the defaults.

**List.** Newest first. Desktop table: date (local), player A, player B, winner, both deltas or "No rating change", status chip when the status filter is not Completed, tournament name. Mobile: one card per match with the same fields. Row → `/matches/{id}`.

**Pager.** "1–20 of {total}" with Previous and Next. Hidden when one page is enough.

**States.** Loading skeletons. No rows: "No matches match these filters." plus Clear. Error with Retry.

---

## Match detail `/matches/[id]`

**Purpose.** Read one result.

**Layout.** One card, max width 720px.

- Status chip when not completed.
- Local date and time.
- Two columns, stacked below 768px: player A and player B. Each: avatar or initials, name (link to profile), "Winner" lime chip on the winner, old → new, signed delta. Inactive chip if `is_active` is false.
- Scores, when present: "21–18 · 18–21", with the caption "Scores are {A name} first. They do not change Elo."
- Tournament name linking to the tournament, when set.
- Notes, when set.
- When `rating_changes` is empty: the sentence "No rating change" in place of the old → new lines.

**States.** Loading skeleton. Unknown or deleted id: "This match isn't on Shuttle Rank." Link to `/matches`. Error with Retry.

---

## Head-to-head `/head-to-head`

**Purpose.** Compare two players on completed matches only.

**Chooser.** Two listboxes, "Player A" and "Player B", options from `GET /players?include_inactive=true`, label "{name} · {rating}" plus an Inactive chip when needed. Choosing either updates `?a=&b=`. If both ids are equal, show "Pick two different players." and do not call the API.

**Result, after a successful load.**

- Summary strip: total matches, "{A} wins" and win rate, "{B} wins" and win rate, "Net Elo for {A}: {player_a_net_rating_change}" with the delta treatment.
- Streak line when set: "{name} has won the last {count}."
- Encounters, newest first: the same row as match history, linking to the match. First five sit under "Recent". The rest sit under "Earlier", hidden behind a disclosure if there are more than five.

**Desktop.** Chooser as two columns, summary as a four-stat strip, list full width. **Mobile.** Stack the two choosers.

**States.** Before both are chosen: "Choose two players." Zero matches: the names plus "No completed matches between these two." Unknown id: not-found. Loading and error on the result region only.

---

## Tournaments `/tournaments` (P6)

**Purpose.** See what is on, what is next, and who won.

**Desktop.** Title "Tournaments". Cards, two columns from 1024px. Card: status chip, name, start date (and end date when set), "{participant_count} players", champion line "Champion {name}" when `champion` is set. Card → `/tournaments/{id}`.

**Order.** As returned (in progress first).

**Mobile.** One column.

**States.** Empty: "No tournaments yet." Loading skeletons. Error with Retry.

---

## Tournament detail `/tournaments/[id]` (P6)

**Purpose.** Read the bracket, the seeds, and the champion.

**Header card.** Name, status chip, dates, description when set. If `champion` is set: Crown, "Champion {name}", muted "Runner-up {runner_up}".

**Participants.** A compact table: seed, player (link), final-position label from R-TN-08. Order as returned (by seed).

**Bracket.** Only when `bracket_generated` is true and `rounds` is non-empty. Otherwise: "The bracket has not been generated."

**Desktop bracket.** One column per round, left to right, earliest round first (`round` ascending). Column title is the payload `name`. Inside a column, slots run in `position` order, top to bottom, spread so a pair sits beside the next match it feeds. Each slot is a small card:

- Player line: seed if set ("1"), name, link to the profile. Empty side of a bye: muted "BYE".
- `completed`: winner's name in lime, link "Match" → `/matches/{match_id}`.
- `pending`: "Waiting".
- `bye`: the advancer plus "BYE". No match link.
- `ready`: both names, no admin button.

Connectors are optional 1px lines. The next column's names are the indication of who advanced. Do not add a bracket library. Do not reorder slots.

**Mobile.** Rounds stack vertically, earliest first. Each slot is a full-width card. No connectors.

**States.** Unknown id: not-found, link to `/tournaments`. Loading: header skeleton and three column skeletons. Error with Retry.

**Example the layout must make obvious (6 players, 8-draw, 2 byes).** Round of 8 has four slots, two of them byes on the top seeds; Semifinals has two ready-or-pending slots; Final has one. A bye card shows the seed and the word BYE, not a blank hole.

---

## Admin login `/admin/login`

**Who.** The single admin.

**Layout.** No public nav and no admin nav. Centered card, max 400px, on `bg`. Title "Admin sign in". Email, password, lime "Sign in". No sign-up link, no "forgot password".

**Error.** "Email or password is not valid." for a rejected sign-in. Rate limit: "Too many attempts. Wait a few minutes." Other failures: "Couldn't reach Shuttle Rank. Try again."

**Success.** Go to `/admin/dashboard`.

---

## Admin overview `/admin/dashboard`

**Purpose.** See whether the club data looks right, then jump to a task.

**Desktop, 12 columns.**

1. Stat cards, four across: players (`players_active` active, `players_total` muted), matches (`matches_completed`, with canceled and disputed as muted counts), tournaments (`tournaments_in_progress` in progress, `tournaments_total` muted), achievements awarded. Under the match card, "Last match {local datetime}" or "No matches yet."
2. Span 7: "Recent activity", ten audit rows (time, action, entity type). "Full log" → `/admin/audit-log`.
3. Span 5: shortcut list, text buttons: Players, Matches, Tournaments, Achievements.

**Mobile.** Stats in a 2×2 grid, then activity, then shortcuts.

**States.** Loading skeletons. Error with Retry. `Dev auth` chip in the shell when `auth_mode` is `dev`.

---

## Admin players `/admin/players`

**Purpose.** Create, edit, deactivate, reactivate.

**List.** All players from `GET /admin/players`, including inactive. Columns: name, Elo (text), highest, W–L, status chip, actions "Edit", "View" (public profile), "Deactivate" or "Reactivate". Primary "New player".

**Dialog fields.** Display name (required, 1–50), avatar URL (optional). On edit, read-only lines for Elo, highest, and W–L. No rating inputs.

**Empty.** "No players yet." and the New player button.

Deactivate and reactivate use the confirmations table. Duplicate name shows the API message under the name field.

---

## Admin matches `/admin/matches`

**Purpose.** Record results and fix mistakes. This is the only place club matches are written.

**List.** `GET /admin/matches` with `status=all`. Same filters as the public list, plus a "Show deleted" checkbox (`include_deleted`). Deleted rows show the Deleted chip and no action buttons.

**Row actions** on a live row: "Notes" (patch dialog: notes and scores only, no confirmation, no replay), "Correct", "Cancel" (hidden when already canceled), "Delete".

**Record dialog.** Player A select, Player B select (active players, label "{name} · {Elo}"), winner as two radios of those names (required), `datetime-local` defaulting to now and blocked past one day ahead, status Completed or Disputed, up to five score rows ("Add game", each side 0–99, A first), notes ≤500. Submit opens "Record this result?" before the POST. A disputed create uses the same dialog and the body says "A disputed match does not change Elo."

**Correct dialog.** Same player, winner, date, and status fields, plus reason. Player fields are omitted when `tournament` is set, with the line "Tournament players come from the bracket." Then the replay confirmation.

**States.** Empty: "No matches yet." and Record. Errors stay in the dialog.

---

## Admin tournaments `/admin/tournaments` and `/admin/tournaments/[id]` (P6)

**List.** Same cards as the public list, plus "New tournament". The card opens the admin detail, not the public page. A "View public page" link sits on the detail header.

**Create / edit dialog.** Name 1–100, description optional, start date, end date. Edit can also cancel, using the cancel-tournament confirmation, only in draft or in progress.

**Detail, draft.** Participant picker (active players not already added), optional seed number, "Add". Remove on each row. Seeding choice: "By current Elo" or "Use assigned seeds". "Generate bracket" is enabled at two or more participants and opens the confirmation.

**Detail, in progress.** Participants are read-only. "Replace bracket" shows only when every slot is unrecorded. The bracket is the public bracket plus a "Record" button on `ready` slots.

**Record slot.** Winner radios of the two names, datetime, optional scores and notes. Then the record confirmation. Players are not editable.

**Completed.** Read-only bracket, champion, runner-up, positions. No generate and no cancel.

**Constraints to surface verbatim** from `error.message`: inactive player, duplicate participant, regenerate blocked, winner change blocked because the next match has a result.

---

## Admin achievements `/admin/achievements` (P6)

**Desktop, two columns.**

1. **Definitions.** List: icon, name, "Inactive" chip when needed, awarded count. "New definition". Dialog: name 1–80, description 1–300, icon select limited to `Trophy`, `Medal`, `Crown`, `Flame`, `Zap`, `Target`, `Star`, `Award`, `Shield`, `Swords`, optional criteria type (plain text) and criteria value, active checkbox. Helper text under criteria: "Stored as a note. Shuttle Rank does not award this automatically."
2. **Awards.** Newest first from `GET /admin/player-achievements`. Columns: player, badge, date, notes, "Revoke". "Award" opens a dialog: player select (active), definition select (active only), optional notes. Then the award confirmation.

**Mobile.** Definitions, then awards.

**Empty.** "No badges yet." / "No awards yet."

---

## Admin audit log `/admin/audit-log`

**Purpose.** See who changed what, especially rating-affecting writes.

**Filters.** Entity type select (all, player, match, tournament, achievement, rankings) and action select including the action names in `docs/API.md`. Changing filters resets to page 1.

**Table.** Local time, actor id, action, entity type, entity id. The row expands in place to show `before_data` and `after_data` as formatted JSON inside `elevated` blocks. Do not pretty-print secrets; these payloads are club data.

**Pager.** Same pattern as matches.

**States.** Empty: "No admin activity yet." Loading skeletons. Error with Retry.

---

## Not-found and global error

Unknown routes use the public shell and the sentence "This page isn't on Shuttle Rank." with a link to `/`. A crashed data fetch never renders a blank card: the region error pattern is required on every block that fetches.
