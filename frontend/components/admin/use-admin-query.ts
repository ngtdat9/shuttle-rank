"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { isUnauthorized } from "@/lib/admin/errors";
import { useAdminAuth } from "@/lib/auth/provider";

type QueryState<T> = {
  loading: boolean;
  data?: T;
  error?: unknown;
};

export function useAdminQuery<T>(
  key: string,
  load: (token: string, signal: AbortSignal) => Promise<T>,
): QueryState<T> & { reload: () => void } {
  const { token, status, expireSession } = useAdminAuth();
  const loadRef = useRef(load);
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState<{
    key: string;
    nonce: number;
    data?: T;
    error?: unknown;
  } | null>(null);

  useEffect(() => {
    loadRef.current = load;
  }, [load]);

  useEffect(() => {
    if (status !== "authenticated" || !token) return;
    const controller = new AbortController();
    let active = true;
    const requestKey = key;
    const requestNonce = nonce;

    loadRef
      .current(token, controller.signal)
      .then((data) => {
        if (!active) return;
        setState({ key: requestKey, nonce: requestNonce, data });
      })
      .catch((error: unknown) => {
        if (!active || controller.signal.aborted) return;
        if (isUnauthorized(error)) {
          expireSession();
          return;
        }
        setState({ key: requestKey, nonce: requestNonce, error });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [expireSession, key, nonce, status, token]);

  const reload = useCallback(() => {
    setNonce((value) => value + 1);
  }, []);

  const settled = state != null && state.key === key && state.nonce === nonce;
  const view: QueryState<T> = {
    loading: !settled,
    data: settled ? state?.data : undefined,
    error: settled ? state?.error : undefined,
  };

  return { ...view, reload };
}

export function useAdminMutation() {
  const { token, expireSession } = useAdminAuth();

  return useCallback(
    async <T>(action: (token: string) => Promise<T>): Promise<T> => {
      if (!token) {
        expireSession();
        throw new Error("Your session ended. Sign in again.");
      }
      try {
        return await action(token);
      } catch (error) {
        if (isUnauthorized(error)) expireSession();
        throw error;
      }
    },
    [expireSession, token],
  );
}
