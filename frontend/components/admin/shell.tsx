"use client";

import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowUpRight,
  Award,
  History,
  LayoutDashboard,
  ScrollText,
  Shield,
  Trophy,
  Users,
  type LucideIcon,
} from "lucide-react";

import { AdminBootSkeleton } from "@/components/admin/ui";
import { ErrorState } from "@/components/error-state";
import { AdminAuthProvider, useAdminAuth } from "@/lib/auth/provider";
import { cn } from "@/lib/utils";

const LINKS: { href: string; label: string; icon: LucideIcon; exact?: boolean }[] = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/admin/players", label: "Players", icon: Users },
  { href: "/admin/matches", label: "Matches", icon: History },
  { href: "/admin/tournaments", label: "Tournaments", icon: Trophy },
  { href: "/admin/achievements", label: "Achievements", icon: Award },
  { href: "/admin/audit-log", label: "Audit log", icon: ScrollText },
];

function AdminHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { admin, authMode, signOut } = useAdminAuth();
  const email = admin?.email ?? admin?.display_name ?? "Admin";
  const devAuth = admin?.auth_mode === "dev" || authMode === "dev";

  return (
    <header className="sticky top-0 z-40 border-t-2 border-t-primary border-b border-b-border bg-surface">
      <div className="mx-auto flex w-full max-w-[1120px] flex-wrap items-center gap-2 px-4 py-3 md:px-8">
        <Link
          href="/admin"
          className="inline-flex items-center gap-2 rounded-full text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Shield className="size-4" strokeWidth={1.75} aria-hidden />
          Admin
        </Link>
        <span className="inline-flex h-5 items-center rounded-full bg-primary/15 px-2 text-xs font-medium text-positive">
          Admin
        </span>
        {devAuth ? (
          <span className="inline-flex h-5 items-center rounded-full bg-warning/15 px-2 text-xs font-medium text-warning">
            Dev auth
          </span>
        ) : null}
        <nav aria-label="Admin" className="flex flex-wrap items-center gap-1">
          {LINKS.map((item) => {
            const active = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-elevated text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="size-4" strokeWidth={1.75} aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <span
            className="max-w-[220px] truncate text-xs text-muted-foreground"
            title={email}
          >
            {email}
          </span>
          <Link
            href="/"
            className="inline-flex h-9 items-center gap-1 rounded-full px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            View public site
            <ArrowUpRight className="size-4" strokeWidth={1.75} aria-hidden />
          </Link>
          <button
            type="button"
            className="inline-flex h-9 items-center rounded-full px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => {
              void signOut().then(() => router.replace("/admin/login"));
            }}
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

function Guarded({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { status, errorMessage, retry, signOut } = useAdminAuth();

  useEffect(() => {
    if (status === "anonymous") router.replace("/admin/login");
  }, [router, status]);

  if (status === "loading" || status === "anonymous") {
    return (
      <main
        id="content"
        className="mx-auto w-full max-w-[1120px] flex-1 px-4 py-6 md:px-8 md:py-8"
      >
        <AdminBootSkeleton />
      </main>
    );
  }

  if (status === "error") {
    return (
      <main
        id="content"
        className="mx-auto flex w-full max-w-[1120px] flex-1 flex-col gap-4 px-4 py-6 md:px-8"
      >
        <ErrorState
          title="Couldn't reach Shuttle Rank. Try again."
          message={errorMessage ?? "The admin session could not be checked."}
          onRetry={retry}
          retryLabel="Retry"
        />
        <button
          type="button"
          className="h-11 w-fit rounded-full border border-border px-4 text-sm md:h-10"
          onClick={() => {
            void signOut().then(() => router.replace("/admin/login"));
          }}
        >
          Sign out
        </button>
      </main>
    );
  }

  return (
    <>
      <AdminHeader />
      <main
        id="content"
        className="mx-auto w-full max-w-[1120px] flex-1 px-4 py-6 md:px-8 md:py-8"
      >
        {children}
      </main>
      <footer className="border-t border-border">
        <p className="mx-auto w-full max-w-[1120px] px-4 py-4 text-xs text-muted-foreground md:px-8">
          Men&apos;s singles · Elo
        </p>
      </footer>
    </>
  );
}

export function AdminFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === "/admin/login";

  return (
    <AdminAuthProvider>
      <div className="flex min-h-screen flex-col bg-background">
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-full focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
        >
          Skip to content
        </a>
        {isLogin ? children : <Guarded>{children}</Guarded>}
      </div>
    </AdminAuthProvider>
  );
}
