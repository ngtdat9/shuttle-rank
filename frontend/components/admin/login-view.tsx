"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  AdminBootSkeleton,
  AdminDialogActions,
  AdminField,
  AdminLiveError,
  adminInputClass,
  adminPrimaryButtonClass,
  describedBy,
} from "@/components/admin/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAdminAuth } from "@/lib/auth/provider";

export function LoginView() {
  const router = useRouter();
  const { status, authMode, errorMessage, loginNotice, signIn } = useAdminAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/admin");
  }, [router, status]);

  if (status === "loading" || status === "authenticated") {
    return (
      <main id="content" className="grid flex-1 place-items-center px-4 py-10">
        <AdminBootSkeleton />
      </main>
    );
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      if (authMode === "dev") {
        await signIn({ token });
      } else {
        await signIn({ email, password });
      }
      router.replace("/admin");
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Couldn't reach Shuttle Rank. Try again.",
      );
    } finally {
      setPending(false);
    }
  }

  const banner = error ?? loginNotice ?? errorMessage;

  return (
    <main
      id="content"
      className="grid flex-1 place-items-center bg-background px-4 py-10"
    >
      <form
        onSubmit={onSubmit}
        className="flex w-full max-w-[400px] flex-col gap-4 rounded-[20px] bg-surface p-6 ring-1 ring-foreground/10"
        noValidate
      >
        <div>
          <p className="text-xs font-medium text-muted-foreground">Shuttle Rank</p>
          <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">
            Admin sign in
          </h1>
        </div>
        {banner ? <AdminLiveError>{banner}</AdminLiveError> : null}
        {authMode === "dev" ? (
          <AdminField
            label="Development token"
            htmlFor="dev-token"
            hint="DEV ONLY. Stored in this tab until you sign out."
            error={null}
          >
            <Input
              id="dev-token"
              className={adminInputClass}
              type="password"
              autoComplete="off"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              aria-describedby={describedBy("dev-token", true, false)}
              required
            />
          </AdminField>
        ) : (
          <>
            <AdminField label="Email" htmlFor="admin-email">
              <Input
                id="admin-email"
                className={adminInputClass}
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </AdminField>
            <AdminField label="Password" htmlFor="admin-password">
              <Input
                id="admin-password"
                className={adminInputClass}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </AdminField>
          </>
        )}
        <AdminDialogActions>
          <Button
            type="submit"
            className={adminPrimaryButtonClass}
            disabled={pending}
            aria-busy={pending}
          >
            {pending ? "Signing in…" : "Sign in"}
          </Button>
        </AdminDialogActions>
      </form>
    </main>
  );
}
