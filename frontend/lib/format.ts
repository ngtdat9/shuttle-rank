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

/** Whole-number rating. Uses the runtime locale unless one is passed. */
export function formatRating(value: number, locale?: Intl.LocalesArgument): string {
  if (!Number.isFinite(value)) {
    return "—";
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Formats a percentage. `value` is 0–100 (78.4 → "78.4%"), not a 0–1 ratio.
 */
export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) {
    return "—";
  }

  const formatted = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(value);

  return `${formatted}%`;
}

/** Signed rating change: +16, -16, or 0. */
export function formatDelta(value: number): string {
  if (!Number.isFinite(value)) {
    return "—";
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 0,
    signDisplay: "exceptZero",
  }).format(value);
}
