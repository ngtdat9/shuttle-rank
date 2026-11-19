const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

const DEFAULT_DATE_OPTIONS: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "short",
  day: "numeric",
};

function parseDateInput(value: string | Date): Date {
  if (value instanceof Date) {
    return value;
  }

  const match = DATE_ONLY.exec(value);
  if (match) {
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    return new Date(year, month - 1, day);
  }

  return new Date(value);
}

/**
 * Formats a date in the given locale, or the runtime locale when omitted.
 * Date-only strings (`YYYY-MM-DD`) are read as a calendar date, not UTC midnight.
 * Pass an explicit locale when the result is server-rendered and must match hydration.
 */
export function formatDate(
  value: string | Date,
  options?: Intl.DateTimeFormatOptions,
  locale?: Intl.LocalesArgument,
): string {
  const date = parseDateInput(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat(locale, {
    ...DEFAULT_DATE_OPTIONS,
    ...options,
  }).format(date);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Whole-number rating with no thousands separator (1516, not 1,516). */
export function formatRating(value: number, locale?: Intl.LocalesArgument): string {
  void locale;
  if (!Number.isFinite(value)) {
    return "—";
  }

  return String(Math.trunc(value));
}

/**
 * Formats a percentage. `value` is 0–100 (78.4 → "78.4%"), not a 0–1 ratio.
 */
export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) {
    return "—";
  }

  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
    useGrouping: false,
  }).format(value);

  return `${formatted}%`;
}

/**
 * Win rate from the API is 0–1, or null when the player has no matches.
 * One decimal percent: 0.5 → "50.0%". Null is an em dash.
 */
export function formatWinRate(rate: number | null | undefined): string {
  if (rate == null || !Number.isFinite(rate)) {
    return "—";
  }

  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    useGrouping: false,
  }).format(rate * 100);

  return `${formatted}%`;
}

/** Signed rating change: +16, −16 (U+2212), or 0. Null is an em dash. */
export function formatDelta(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }

  const rounded = Math.trunc(value);
  if (rounded > 0) return `+${rounded}`;
  if (rounded < 0) return `\u2212${Math.abs(rounded)}`;
  return "0";
}

/** W–L record with an en dash, for example 12–7. */
export function formatRecord(wins: number, losses: number): string {
  return `${wins}\u2013${losses}`;
}

/** Two-digit rank label. The number itself is the API rank, including ties. */
export function formatRank(rank: number): string {
  return String(Math.trunc(rank)).padStart(2, "0");
}

/** Calendar label such as "Nov 2026". */
export function formatMonthLabel(year: number, month: number): string {
  const name = MONTHS[month - 1];
  if (!name) return "—";
  return `${name} ${year}`;
}

export function isCurrentUtcMonth(year: number, month: number, now = new Date()): boolean {
  return now.getUTCFullYear() === year && now.getUTCMonth() + 1 === month;
}

/** Game scores with player A first: "21–18 · 18–21". */
export function formatGameScores(scores: [number, number][] | null | undefined): string | null {
  if (!scores || scores.length === 0) return null;
  return scores.map(([a, b]) => `${a}\u2013${b}`).join(" · ");
}
