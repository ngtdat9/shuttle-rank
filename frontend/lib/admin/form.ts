import { formatDate } from "@/lib/format";

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** Local datetime suitable for `<input type="datetime-local">`. */
export function toDatetimeLocal(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function nowDatetimeLocal(now = new Date()): string {
  return toDatetimeLocal(now);
}

/** One day ahead, the latest match time the API accepts. */
export function maxMatchDatetimeLocal(now = new Date()): string {
  return toDatetimeLocal(new Date(now.getTime() + 24 * 60 * 60 * 1000));
}

/** Converts a datetime-local value to an ISO UTC string. */
export function datetimeLocalToUtc(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

export function isMoreThanOneDayAhead(value: string, now = new Date()): boolean {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return true;
  return date.getTime() > now.getTime() + 24 * 60 * 60 * 1000;
}

export function formatLocalWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return formatDate(date, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export type ScoreRow = { a: string; b: string };

export function scoresFromApi(
  scores: [number, number][] | null | undefined,
): ScoreRow[] {
  if (!scores || scores.length === 0) return [];
  return scores.map(([a, b]) => ({ a: String(a), b: String(b) }));
}

export function parseScores(
  rows: ScoreRow[],
): { ok: true; value: [number, number][] | null } | { ok: false; message: string } {
  const filled = rows.filter((row) => row.a.trim() !== "" || row.b.trim() !== "");
  if (filled.length === 0) return { ok: true, value: null };
  if (filled.length > 5) return { ok: false, message: "At most five games." };

  const value: [number, number][] = [];
  for (const row of filled) {
    if (row.a.trim() === "" || row.b.trim() === "") {
      return { ok: false, message: "Enter both scores for each game." };
    }
    const a = Number(row.a);
    const b = Number(row.b);
    if (
      !Number.isInteger(a) ||
      !Number.isInteger(b) ||
      a < 0 ||
      a > 99 ||
      b < 0 ||
      b > 99
    ) {
      return { ok: false, message: "Each score is a whole number from 0 to 99." };
    }
    value.push([a, b]);
  }
  return { ok: true, value };
}

export function optionalText(
  value: string,
  max: number,
): { ok: true; value: string | null } | { ok: false; message: string } {
  const trimmed = value.trim();
  if (!trimmed) return { ok: true, value: null };
  if (trimmed.length > max)
    return { ok: false, message: `Use at most ${max} characters.` };
  return { ok: true, value: trimmed };
}

export function requiredReason(
  value: string,
): { ok: true; value: string } | { ok: false; message: string } {
  const trimmed = value.trim();
  if (trimmed.length < 1 || trimmed.length > 500) {
    return { ok: false, message: "Reason must be 1–500 characters." };
  }
  return { ok: true, value: trimmed };
}
