"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import { getAdminMe } from "@/lib/api/admin";
import { isApiError } from "@/lib/admin/errors";
import { resolveAuthMode, type AuthMode } from "@/lib/auth/mode";
import { clearDevToken, readDevToken, writeDevToken } from "@/lib/auth/session";
import { getSupabaseClient } from "@/lib/auth/supabase";
import type { AdminMe } from "@/types/api";

export type AdminAuthStatus = "loading" | "authenticated" | "anonymous" | "error";

type AuthState = {
  status: AdminAuthStatus;
  token: string | null;
  admin: AdminMe | null;
  errorMessage: string | null;
};

type SignInInput = { email: string; password: string } | { token: string };

type AdminAuthContextValue = AuthState & {
  authMode: AuthMode;
  signIn: (input: SignInInput) => Promise<void>;
  signOut: () => Promise<void>;
  expireSession: () => void;
  retry: () => void;
  loginNotice: string | null;
};

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null);

const anonymousState: AuthState = {
  status: "anonymous",
  token: null,
  admin: null,
  errorMessage: null,
};

function mapSupabaseFailure(error: { message?: string; status?: number }): Error {
  const status = error.status ?? 0;
  const message = (error.message ?? "").toLowerCase();
  if (status === 429 || message.includes("rate limit")) {
    return new Error("Too many attempts. Wait a few minutes.");
  }
  if (
    status === 0 ||
    message.includes("fetch") ||
    message.includes("network") ||
    message.includes("failed to reach")
  ) {
    return new Error("Couldn't reach Shuttle Rank. Try again.");
  }
  return new Error("Email or password is not valid.");
}

function mapAdminCheck(error: unknown, mode: AuthMode): Error {
  if (isApiError(error)) {
    if (error.status === 403) return new Error("This account is not an administrator.");
    if (error.status === 429)
      return new Error("Too many attempts. Wait a few minutes.");
    if (error.status === 0) return new Error("Couldn't reach Shuttle Rank. Try again.");
    if (error.status === 401) {
      return new Error(
        mode === "dev"
          ? "That development token was rejected."
          : "Email or password is not valid.",
      );
    }
  }
  return new Error("Couldn't reach Shuttle Rank. Try again.");
}

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const authMode = resolveAuthMode();
  const [attempt, setAttempt] = useState(0);
  const [loginNotice, setLoginNotice] = useState<string | null>(null);
  const [state, setState] = useState<AuthState>({
    status: "loading",
    token: null,
    admin: null,
    errorMessage: null,
  });

  const signOut = useCallback(async () => {
    setState(anonymousState);
    clearDevToken();
    if (authMode === "supabase") {
      const supabase = getSupabaseClient();
      if (supabase) {
        await supabase.auth.signOut();
      }
    }
  }, [authMode]);

  const expireSession = useCallback(() => {
    setLoginNotice("Your session ended. Sign in again.");
    void signOut();
    router.replace("/admin/login");
  }, [router, signOut]);

  const retry = useCallback(() => {
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const supabase = authMode === "supabase" ? getSupabaseClient() : null;

    const subscription = supabase?.auth.onAuthStateChange((event, session) => {
      if (event === "TOKEN_REFRESHED" && session?.access_token) {
        const access = session.access_token;
        setState((current) => {
          if (current.status !== "authenticated") return current;
          return { ...current, token: access };
        });
      }
    });

    async function boot() {
      setState({ status: "loading", token: null, admin: null, errorMessage: null });
      try {
        if (authMode === "dev") {
          const stored = readDevToken();
          if (!stored) {
            if (!cancelled) setState(anonymousState);
            return;
          }
          const admin = await getAdminMe(stored);
          if (cancelled) return;
          setState({
            status: "authenticated",
            token: stored,
            admin,
            errorMessage: null,
          });
          return;
        }

        if (!supabase) {
          if (!cancelled) {
            setState({
              status: "error",
              token: null,
              admin: null,
              errorMessage: "Supabase sign-in is not configured.",
            });
          }
          return;
        }

        const { data, error } = await supabase.auth.getSession();
        if (error) throw error;
        const access = data.session?.access_token;
        if (!access) {
          if (!cancelled) setState(anonymousState);
          return;
        }
        const admin = await getAdminMe(access);
        if (cancelled) return;
        setState({ status: "authenticated", token: access, admin, errorMessage: null });
      } catch (error) {
        if (cancelled) return;
        if (!isApiError(error) || error.status === 0) {
          setState({
            status: "error",
            token: null,
            admin: null,
            errorMessage: "Couldn't reach Shuttle Rank. Try again.",
          });
          return;
        }
        clearDevToken();
        if (supabase) {
          await supabase.auth.signOut();
        }
        if (cancelled) return;
        if (isApiError(error) && error.status === 403) {
          setLoginNotice("This account is not an administrator.");
        } else if (isApiError(error) && error.status === 429) {
          setLoginNotice("Too many attempts. Wait a few minutes.");
        }
        setState(anonymousState);
      }
    }

    void boot();
    return () => {
      cancelled = true;
      subscription?.data.subscription.unsubscribe();
    };
  }, [attempt, authMode]);

  const signIn = useCallback(
    async (input: SignInInput) => {
      if (authMode === "dev") {
        if (!("token" in input)) {
          throw new Error("Enter the development token.");
        }
        const token = input.token.trim();
        if (!token) throw new Error("Enter the development token.");
        writeDevToken(token);
        try {
          const admin = await getAdminMe(token);
          setLoginNotice(null);
          setState({ status: "authenticated", token, admin, errorMessage: null });
        } catch (error) {
          clearDevToken();
          if (isApiError(error) && error.status === 403) {
            throw new Error("This account is not an administrator.");
          }
          throw mapAdminCheck(error, "dev");
        }
        return;
      }

      if (!("email" in input)) {
        throw new Error("Email or password is not valid.");
      }
      const supabase = getSupabaseClient();
      if (!supabase) {
        throw new Error("Supabase sign-in is not configured.");
      }
      const { data, error } = await supabase.auth.signInWithPassword({
        email: input.email.trim(),
        password: input.password,
      });
      if (error || !data.session?.access_token) {
        throw mapSupabaseFailure(
          error ?? { message: "Invalid login credentials", status: 400 },
        );
      }
      const token = data.session.access_token;
      try {
        const admin = await getAdminMe(token);
        setLoginNotice(null);
        setState({ status: "authenticated", token, admin, errorMessage: null });
      } catch (checkError) {
        await supabase.auth.signOut();
        throw mapAdminCheck(checkError, "supabase");
      }
    },
    [authMode],
  );

  const value = useMemo<AdminAuthContextValue>(
    () => ({
      ...state,
      authMode,
      signIn,
      signOut,
      expireSession,
      retry,
      loginNotice,
    }),
    [authMode, expireSession, loginNotice, retry, signIn, signOut, state],
  );

  return (
    <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>
  );
}

export function useAdminAuth(): AdminAuthContextValue {
  const value = useContext(AdminAuthContext);
  if (!value) {
    throw new Error("useAdminAuth must be used within AdminAuthProvider.");
  }
  return value;
}
