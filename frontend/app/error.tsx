"use client";

import { ErrorState } from "@/components/error-state";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ErrorState
      title="Couldn't load this page."
      message={error.digest ? "Try again." : "Try again."}
      onRetry={reset}
      retryLabel="Retry"
    />
  );
}
