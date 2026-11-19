# Elo algorithm

Men's singles use one winner-only result. There is no score margin. The backend
is the only place that calculates ratings. Decisions D-004 and D-007 fix the
parameters and the rounding. Decision D-014 fixes how corrections are replayed.

## Parameters

| Setting | Value |
| --- | --- |
| Starting rating | 1500 |
| K-factor | 32 |
| Scale divisor | 400 |
| Result | winner `1`, loser `0` |

Expected score for a player rated `R` against an opponent rated `O`:

```text
E = 1 / (1 + 10 ^ ((O - R) / 400))
```

The two expected scores sum to 1.

## Integer delta (D-007)

Python's `round` uses banker's rounding, so `round(16.5)` is `16`. The app
does not use that. It takes one integer delta from the winner's side and
rounds half up:

```text
delta = floor(K * (1 - E_winner) + 0.5)
```

The winner's new rating is `old + delta`. The loser's new rating is `old - delta`.
The same integer is moved both ways, so the club's total rating points stay
constant even when the raw value lands on a half.

Only `completed` matches with `deleted_at` unset are rated. Canceled and
disputed matches write no `rating_history` rows. A match is never rated twice.
The service checks for an existing history row first; the unique constraint on
`rating_history(match_id, player_id)` is the backstop.

`highest_rating` is `max(1500, every new_rating the player has had)`. It is not
edited by hand and it does not fall when the player loses, unless a replay
removes the match that set the peak.

### Worked examples

Equal ratings, the required base case:

```text
E_winner = 0.5
delta = floor(32 * (1 - 0.5) + 0.5) = floor(16.5) = 16
1500 vs 1500 -> winner 1516, loser 1484
```

Favorite wins. Winner 1600, loser 1400:

```text
E_winner = 1 / (1 + 10 ^ (-200 / 400)) ≈ 0.759747
delta = floor(32 * (1 - 0.759747) + 0.5) = floor(8.188) = 8
1600 vs 1400 -> winner 1608, loser 1392
```

Underdog wins. Winner 1400, loser 1600:

```text
E_winner ≈ 0.240253
delta = floor(32 * 0.759747 + 0.5) = floor(24.812) = 24
1400 vs 1600 -> winner 1424, loser 1576
```

Half-up versus banker's rounding. Equal ratings make the raw change exactly
`K / 2`. With `K = 33` that raw change is `16.5`:

```text
delta = floor(33 * 0.5 + 0.5) = floor(17.0) = 17
round(16.5) = 16   # Python banker's rounding, not used
```

## Processing order

Rated matches are applied in order of `(match_date, created_at, id)`, all in
UTC. The rating used for a match is the rating each player had after the
previous rated match in that order, or 1500 if they have none.

A new completed match whose key is strictly after every existing rated match
is applied incrementally: both players' `current_rating` values are the
pre-match ratings, two `rating_history` rows are inserted, and `current_rating`
and `highest_rating` are updated. Anything else that can change a later rating
uses the replay below.

## Replay (D-014)

Replay runs for a backdated create, a correction, a cancellation, a soft
delete, and any status change. The whole replay, the audit row, and the
monthly snapshot rebuild share one database transaction.

1. Find the earliest affected order key. For a correction that also moves the
   date, that is the earlier of the old key and the new key. For a cancel,
   delete, or status change, it is the match's current key. For a backdated
   create, it is the new match's key.
2. Remember each player's rating just before that key: the `new_rating` on
   their latest `rating_history` row whose match sorts before the key, or
   1500 when they have no earlier row.
3. Delete `rating_history` rows for matches that sort at or after the key.
   This includes a match that just stopped being rated (canceled or soft-deleted)
   so its old rows cannot linger.
4. Walk every match that is still rated at or after the key, in order. Rate
   each one from the remembered pre-key ratings, then from the running ratings
   of this replay. Do not read `current_rating` for this walk; it still
   includes the results being replaced.
5. Recompute each affected player's stored ratings from the history that
   remains. `current_rating` is the latest `new_rating`, or 1500 if none
   remain. `highest_rating` is `max(1500, every remaining new_rating)`.
   Players whose only matches were removed go back to 1500 / 1500. Players
   who only played before the cutoff are left untouched.

`recalculate_all` deletes every history row, resets every player to 1500, and
rates every current rated match from scratch. A correct replay and a full
recalculation produce the same `current_rating`, `highest_rating`, and the
same history values (match, player, old, new, change).

### Replay example

January 2: A beats B from 1500–1500. A is 1516, B is 1484.

January 3: A beats B again. The pre-match ratings are 1516 and 1484, not 1500,
so A gains fewer than 16 points.

Correct January 2 so that B won instead. The cutoff is January 2.

- Ratings before that point are 1500 and 1500. History for both matches is deleted.
- January 2 is replayed as B's win: B 1516, A 1484.
- January 3 is replayed from those ratings. A is the underdog, so A gains more
  than 16 and B drops by the same amount.
- `highest_rating` is rebuilt from the new history. The peak A reached on the
  original January 2 no longer exists, so it is not kept.

Cancel or soft-delete the only match between two players and both return to
1500, with no history rows left.
