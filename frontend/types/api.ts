/**
 * Types for docs/API.md. Field names match the contract.
 * The frontend displays these values and does not derive ratings or ranks.
 */

export type FormResult = "W" | "L";

export type PlayerSummary = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  current_rating: number;
  is_active: boolean;
};

export type PlayerStats = {
  matches_played: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  current_streak: { type: FormResult; count: number } | null;
  recent_form: FormResult[];
  last_rating_change: number | null;
  rating_change_30d: number;
};

export type RankingEntry = {
  rank: number;
  player: PlayerSummary;
  rating: number;
  highest_rating: number;
  matches_played: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  last_rating_change: number | null;
  rating_change_30d: number;
  recent_form: FormResult[];
};

export type RatingChange = {
  player_id: string;
  old_rating: number;
  new_rating: number;
  rating_change: number;
};

export type MatchStatus = "completed" | "canceled" | "disputed";

export type MatchListStatus = MatchStatus | "all";

export type Match = {
  id: string;
  player_a: PlayerSummary;
  player_b: PlayerSummary;
  winner_id: string;
  match_date: string;
  status: MatchStatus;
  tournament: { id: string; name: string } | null;
  game_scores: [number, number][] | null;
  notes: string | null;
  rating_changes: RatingChange[];
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PlayerMatch = Match & {
  opponent: PlayerSummary;
  result: FormResult;
  rating_change: number | null;
};

export type Achievement = {
  id: string;
  name: string;
  description: string;
  icon: string;
  criteria_type: string;
  criteria_value: number | null;
  is_active: boolean;
  awarded_count: number;
};

export type PlayerAchievement = {
  id: string;
  achievement: Achievement;
  awarded_at: string;
  notes: string | null;
};

export type AchievementAward = {
  id: string;
  player: PlayerSummary;
  achievement: Achievement;
  awarded_at: string;
};

export type TournamentStatus = "draft" | "in_progress" | "completed" | "canceled";

export type TournamentSummary = {
  id: string;
  name: string;
  description: string | null;
  format: "single_elimination";
  status: TournamentStatus;
  start_date: string | null;
  end_date: string | null;
  participant_count: number;
  champion: PlayerSummary | null;
  created_at: string;
};

export type TournamentParticipant = {
  player: PlayerSummary;
  seed: number | null;
  final_position: number | null;
};

export type TournamentDetail = TournamentSummary & {
  participants: TournamentParticipant[];
  bracket_generated: boolean;
  runner_up: PlayerSummary | null;
  updated_at: string;
};

export type BracketMatchStatus = "pending" | "ready" | "completed" | "bye";

export type BracketMatch = {
  id: string;
  round: number;
  position: number;
  player_a: PlayerSummary | null;
  player_b: PlayerSummary | null;
  seed_a: number | null;
  seed_b: number | null;
  winner_id: string | null;
  is_bye: boolean;
  status: BracketMatchStatus;
  match_id: string | null;
  match_date: string | null;
  game_scores: [number, number][] | null;
};

export type BracketRound = {
  round: number;
  name: string;
  matches: BracketMatch[];
};

export type Bracket = {
  tournament_id: string;
  rounds: BracketRound[];
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: unknown;
  };
};

export type HealthResponse = {
  status: string;
  database: string;
};

export type DashboardTotals = {
  active_players: number;
  total_matches: number;
  matches_this_month: number;
  tournaments_completed: number;
};

export type RatingProgressionPoint = {
  match_date: string | null;
  rating: number;
};

export type RatingProgressionSeries = {
  player: PlayerSummary;
  points: RatingProgressionPoint[];
};

export type Dashboard = {
  leader: RankingEntry | null;
  top_players: RankingEntry[];
  totals: DashboardTotals;
  recent_matches: Match[];
  rating_progression: RatingProgressionSeries[];
  active_tournament: TournamentSummary | null;
  recent_achievements: AchievementAward[];
  last_updated: string | null;
};

export type RankingSort =
  | "rank"
  | "rating"
  | "win_rate"
  | "wins"
  | "losses"
  | "matches_played"
  | "highest_rating";

export type SortOrder = "asc" | "desc";

export type RankingsResponse = {
  items: RankingEntry[];
  last_updated: string | null;
};

export type MonthRef = {
  year: number;
  month: number;
};

export type MonthlyRankingItem = {
  rank: number;
  player: PlayerSummary;
  rating: number;
  rank_change: number | null;
  wins: number;
  losses: number;
  matches_played: number;
  rating_change_during_month: number;
};

export type MonthlyRankingsResponse = {
  available_months: MonthRef[];
  year: number | null;
  month: number | null;
  items: MonthlyRankingItem[];
};

export type PlayerListItem = PlayerSummary & {
  highest_rating: number;
  rank: number | null;
  matches_played: number;
  wins: number;
  losses: number;
  win_rate: number | null;
};

export type PlayerListResponse = {
  items: PlayerListItem[];
};

export type PlayerProfile = PlayerSummary & {
  highest_rating: number;
  rank: number | null;
  stats: PlayerStats;
  created_at: string;
  updated_at: string;
};

export type RatingHistoryPoint = {
  match_id: string;
  match_date: string;
  old_rating: number;
  new_rating: number;
  rating_change: number;
  opponent: PlayerSummary;
  result: FormResult;
};

export type RatingHistoryResponse = {
  player_id: string;
  starting_rating: 1500;
  points: RatingHistoryPoint[];
};

export type PlayerMonthlyItem = {
  year: number;
  month: number;
  rating: number;
  rank: number;
  wins: number;
  losses: number;
  matches_played: number;
  rating_change_during_month: number;
};

export type PlayerMonthlyResponse = {
  items: PlayerMonthlyItem[];
};

export type PlayerAchievementListResponse = {
  items: PlayerAchievement[];
};

export type HeadToHead = {
  player_a: PlayerSummary;
  player_b: PlayerSummary;
  total_matches: number;
  player_a_wins: number;
  player_b_wins: number;
  player_a_win_rate: number | null;
  player_b_win_rate: number | null;
  current_streak: { player_id: string; count: number } | null;
  player_a_net_rating_change: number;
  matches: Match[];
};

export type TournamentListResponse = {
  items: TournamentSummary[];
};

export type AchievementListResponse = {
  items: Achievement[];
};

export type AdminMe = {
  id: string;
  email: string | null;
  display_name: string | null;
  auth_mode: "supabase" | "dev";
};

export type AdminStats = {
  players_total: number;
  players_active: number;
  matches_total: number;
  matches_completed: number;
  matches_canceled: number;
  matches_disputed: number;
  tournaments_total: number;
  tournaments_in_progress: number;
  achievements_awarded: number;
  last_match_at: string | null;
};

export type AuditLogEntry = {
  id: string;
  actor_id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before_data: unknown;
  after_data: unknown;
  created_at: string;
};

export type CreatePlayerBody = {
  display_name: string;
  avatar_url?: string | null;
};

export type UpdatePlayerBody = {
  display_name?: string;
  avatar_url?: string | null;
  is_active?: boolean;
};

export type CreateMatchBody = {
  player_a_id: string;
  player_b_id: string;
  winner_id: string;
  match_date: string;
  status?: "completed" | "disputed";
  game_scores?: [number, number][] | null;
  notes?: string | null;
};

export type PatchMatchBody = {
  notes?: string | null;
  game_scores?: [number, number][] | null;
};

export type CorrectMatchBody = {
  player_a_id?: string;
  player_b_id?: string;
  winner_id?: string;
  match_date?: string;
  status?: MatchStatus;
  reason: string;
};

export type CancelMatchBody = {
  reason: string;
};

export type DeletedEntity = {
  id: string;
  deleted: true;
};

export type CreateTournamentBody = {
  name: string;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
};

export type UpdateTournamentBody = {
  name?: string;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status?: "canceled";
};

export type TournamentParticipantInput = {
  player_id: string;
  seed?: number | null;
};

export type AddParticipantsBody = {
  participants: TournamentParticipantInput[];
};

export type GenerateBracketBody = {
  seeding?: "rating" | "manual";
};

export type RecordBracketMatchBody = {
  bracket_match_id: string;
  winner_id: string;
  match_date: string;
  game_scores?: [number, number][] | null;
  notes?: string | null;
};

export type RecordBracketMatchResponse = {
  match: Match;
  bracket: Bracket;
};

export type CreateAchievementBody = {
  name: string;
  description: string;
  icon?: string;
  criteria_type?: string;
  criteria_value?: number | null;
};

export type UpdateAchievementBody = {
  name?: string;
  description?: string;
  icon?: string;
  criteria_type?: string;
  criteria_value?: number | null;
  is_active?: boolean;
};

export type AwardAchievementBody = {
  achievement_id: string;
  notes?: string | null;
};

export type AdminPlayerAchievement = AchievementAward & {
  notes: string | null;
  awarded_by: string;
};

export type MonthlyRebuildResponse = {
  months_rebuilt: number;
};
