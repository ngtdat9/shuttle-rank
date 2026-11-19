import type { BracketMatch, BracketRound, PlayerSummary } from "@/types/api";

/**
 * Sample props for the /design showcase only.
 * These are not club data and are not fetched from the API.
 */

function player(id: string, displayName: string, rating: number): PlayerSummary {
  return {
    id,
    display_name: displayName,
    avatar_url: null,
    current_rating: rating,
    is_active: true,
  };
}

const minh = player("sample-minh", "Minh Tran", 1284);
const kenji = player("sample-kenji", "Kenji Sato", 1240);
const luca = player("sample-luca", "Luca Rossi", 1211);
const omar = player("sample-omar", "Omar Haddad", 1176);
const theo = player("sample-theo", "Theo Nguyen", 1142);
const anika = player("sample-anika", "Anika Shah", 1120);
const pedro = player("sample-pedro", "Pedro Alves", 1098);
const wei = player("sample-wei", "Wei Chen", 1074);

function match(
  partial: Pick<BracketMatch, "id" | "round" | "position" | "status"> &
    Partial<BracketMatch>,
): BracketMatch {
  return {
    player_a: null,
    player_b: null,
    seed_a: null,
    seed_b: null,
    winner_id: null,
    is_bye: false,
    match_id: null,
    match_date: null,
    game_scores: null,
    ...partial,
  };
}

function bye(
  id: string,
  round: number,
  position: number,
  advancer: PlayerSummary,
  seed: number,
): BracketMatch {
  return match({
    id,
    round,
    position,
    status: "bye",
    is_bye: true,
    player_a: advancer,
    seed_a: seed,
    winner_id: advancer.id,
  });
}

/** Five players in an 8-draw: three byes, one played quarterfinal. */
export const SAMPLE_BRACKET_FIVE: BracketRound[] = [
  {
    round: 1,
    name: "Quarterfinals",
    matches: [
      bye("sample-5-r1-0", 1, 0, minh, 1),
      match({
        id: "sample-5-r1-1",
        round: 1,
        position: 1,
        status: "completed",
        player_a: omar,
        player_b: theo,
        seed_a: 4,
        seed_b: 5,
        winner_id: omar.id,
        match_id: "sample-match-omar-theo",
        match_date: "2026-03-02T10:00:00Z",
        game_scores: [
          [21, 18],
          [19, 21],
          [21, 16],
        ],
      }),
      bye("sample-5-r1-2", 1, 2, kenji, 2),
      bye("sample-5-r1-3", 1, 3, luca, 3),
    ],
  },
  {
    round: 2,
    name: "Semifinals",
    matches: [
      match({
        id: "sample-5-r2-0",
        round: 2,
        position: 0,
        status: "ready",
        player_a: minh,
        player_b: omar,
        seed_a: 1,
        seed_b: 4,
      }),
      match({
        id: "sample-5-r2-1",
        round: 2,
        position: 1,
        status: "ready",
        player_a: kenji,
        player_b: luca,
        seed_a: 2,
        seed_b: 3,
      }),
    ],
  },
  {
    round: 3,
    name: "Final",
    matches: [
      match({
        id: "sample-5-r3-0",
        round: 3,
        position: 0,
        status: "pending",
      }),
    ],
  },
];

/** Eight players, no byes. One semifinal is still waiting on a quarterfinal. */
export const SAMPLE_BRACKET_EIGHT: BracketRound[] = [
  {
    round: 1,
    name: "Quarterfinals",
    matches: [
      match({
        id: "sample-8-r1-0",
        round: 1,
        position: 0,
        status: "completed",
        player_a: minh,
        player_b: wei,
        seed_a: 1,
        seed_b: 8,
        winner_id: minh.id,
        match_id: "sample-match-minh-wei",
        match_date: "2026-04-04T09:00:00Z",
        game_scores: [
          [21, 14],
          [21, 17],
        ],
      }),
      match({
        id: "sample-8-r1-1",
        round: 1,
        position: 1,
        status: "completed",
        player_a: omar,
        player_b: theo,
        seed_a: 4,
        seed_b: 5,
        winner_id: theo.id,
        match_id: "sample-match-omar-theo-8",
        match_date: "2026-04-04T09:40:00Z",
        game_scores: [
          [18, 21],
          [21, 19],
          [15, 21],
        ],
      }),
      match({
        id: "sample-8-r1-2",
        round: 1,
        position: 2,
        status: "ready",
        player_a: kenji,
        player_b: pedro,
        seed_a: 2,
        seed_b: 7,
      }),
      match({
        id: "sample-8-r1-3",
        round: 1,
        position: 3,
        status: "completed",
        player_a: luca,
        player_b: anika,
        seed_a: 3,
        seed_b: 6,
        winner_id: luca.id,
        match_id: "sample-match-luca-anika",
        match_date: "2026-04-04T10:20:00Z",
        game_scores: [[21, 12]],
      }),
    ],
  },
  {
    round: 2,
    name: "Semifinals",
    matches: [
      match({
        id: "sample-8-r2-0",
        round: 2,
        position: 0,
        status: "ready",
        player_a: minh,
        player_b: theo,
        seed_a: 1,
        seed_b: 5,
      }),
      match({
        id: "sample-8-r2-1",
        round: 2,
        position: 1,
        status: "pending",
        player_b: luca,
        seed_b: 3,
      }),
    ],
  },
  {
    round: 3,
    name: "Final",
    matches: [
      match({
        id: "sample-8-r3-0",
        round: 3,
        position: 0,
        status: "pending",
      }),
    ],
  },
];
