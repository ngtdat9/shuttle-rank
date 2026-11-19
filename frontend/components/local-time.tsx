"use client";

import { useEffect, useState } from "react";

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
 * Formats a UTC instant. The server render and first client paint use UTC with
 * the en-US locale (identical, so no hydration mismatch); after mount it switches
 * to the viewer's local timezone.
 */
export function LocalDateTime({
  value,
  withTime = true,
}: {
  value: string;
  withTime?: boolean;
}) {
  const [timeZone, setTimeZone] = useState<string | undefined>(undefined);

  useEffect(() => {
    // Post-mount only: the viewer's zone is unknown during server render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone);
  }, []);

  const text = formatDate(value, { ...(withTime ? DATE_TIME : DATE_ONLY), timeZone });
  return (
    <time dateTime={value} title={value}>
      {text}
    </time>
  );
}
