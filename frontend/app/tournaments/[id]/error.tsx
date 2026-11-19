"use client";

import { ErrorState } from "@/components/error-state";

export default function TournamentError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ErrorState
      title="Couldn't load this tournament."
      message={error.digest ? "Try again." : "Try again."}
      onRetry={reset}
      retryLabel="Retry"
    />
  );
}
