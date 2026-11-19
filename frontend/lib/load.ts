import { notFound } from "next/navigation";

import { ApiError, isApiError } from "@/lib/api/client";

export type LoadResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

export async function loadData<T>(
  request: Promise<T>,
  options?: { notFoundOn404?: boolean },
): Promise<LoadResult<T>> {
  try {
    const data = await request;
    return { ok: true, data };
  } catch (error) {
    if (isApiError(error)) {
      if (options?.notFoundOn404 && error.status === 404) {
        notFound();
      }
      return { ok: false, error };
    }
    throw error;
  }
}

export function errorCopy(error: ApiError, thing: string): { title: string; message: string } {
  if (error.status === 0 || error.code === "network_error") {
    return {
      title: "Couldn't reach Shuttle Rank.",
      message: "Try again.",
    };
  }
  return {
    title: `Couldn't load ${thing}.`,
    message: "Try again.",
  };
}
