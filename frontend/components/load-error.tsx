"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/error-state";

export function LoadError({
  title,
  message,
}: {
  title: string;
  message?: string;
}) {
  const router = useRouter();
  return (
    <ErrorState
      title={title}
      message={message}
      retryLabel="Retry"
      onRetry={() => router.refresh()}
    />
  );
}
