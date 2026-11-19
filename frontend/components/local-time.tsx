"use client";

import { formatDate } from "@/lib/format";

const DATE_TIME: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
};

const DATE_ONLY: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "short",
  day: "numeric",
};

/**
 * Formats a UTC instant in the viewer's timezone.
 * suppressHydrationWarning covers the server timezone differing from the browser.
 */
export function LocalDateTime({
  value,
  withTime = true,
}: {
  value: string;
  withTime?: boolean;
}) {
  const text = formatDate(value, withTime ? DATE_TIME : DATE_ONLY);
  return (
    <time dateTime={value} title={value} suppressHydrationWarning>
      {text}
    </time>
  );
}
