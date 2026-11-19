import { ApiError, isApiError } from "@/lib/api/client";

export function apiErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.status === 0) return "Couldn't reach Shuttle Rank. Try again.";
    if (error.status === 429) return "Too many attempts. Wait a few minutes.";
    const details = formatDetails(error.details);
    if (error.code === "validation_error" && details) return details;
    if (error.message) return error.message;
  }
  if (error instanceof Error && error.message) return error.message;
  return "Couldn't reach Shuttle Rank. Try again.";
}

export function fieldError(error: unknown, field: string): string | null {
  if (!isApiError(error) || error.details == null) return null;
  const details = error.details;
  if (Array.isArray(details)) {
    for (const item of details) {
      if (!item || typeof item !== "object") continue;
      const record = item as { loc?: unknown; msg?: unknown; message?: unknown };
      const loc = Array.isArray(record.loc) ? record.loc.map(String) : [];
      if (!loc.includes(field)) continue;
      if (typeof record.msg === "string" && record.msg) return record.msg;
      if (typeof record.message === "string" && record.message) return record.message;
    }
    return null;
  }
  if (typeof details === "object") {
    const value = (details as Record<string, unknown>)[field];
    if (typeof value === "string" && value) return value;
    if (Array.isArray(value)) {
      const first = value.find((entry) => typeof entry === "string");
      if (typeof first === "string") return first;
    }
  }
  return null;
}

function formatDetails(details: unknown): string | null {
  if (details == null) return null;
  if (typeof details === "string" && details.trim()) return details;
  if (Array.isArray(details)) {
    const lines = details
      .map((item) => {
        if (typeof item === "string") return item;
        if (!item || typeof item !== "object") return null;
        const record = item as { loc?: unknown; msg?: unknown; message?: unknown };
        const msg =
          typeof record.msg === "string"
            ? record.msg
            : typeof record.message === "string"
              ? record.message
              : null;
        if (!msg) return null;
        const loc = Array.isArray(record.loc)
          ? record.loc.map(String).filter((part) => part !== "body" && part !== "query")
          : [];
        return loc.length > 0 ? `${loc.join(".")}: ${msg}` : msg;
      })
      .filter((line): line is string => Boolean(line));
    return lines.length > 0 ? lines.join(" ") : null;
  }
  if (typeof details === "object") {
    const lines = Object.entries(details as Record<string, unknown>)
      .map(([key, value]) => {
        if (typeof value === "string") return `${key}: ${value}`;
        if (Array.isArray(value)) {
          const text = value.filter((entry) => typeof entry === "string").join(", ");
          return text ? `${key}: ${text}` : null;
        }
        return null;
      })
      .filter((line): line is string => Boolean(line));
    return lines.length > 0 ? lines.join(" ") : null;
  }
  return null;
}

export function isUnauthorized(error: unknown): boolean {
  return isApiError(error) && error.status === 401;
}

export function isForbidden(error: unknown): boolean {
  return isApiError(error) && error.status === 403;
}

export { ApiError, isApiError };
