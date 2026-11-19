"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  GitCompare,
  History,
  LayoutDashboard,
  ListOrdered,
  Trophy,
  Users,
  type LucideIcon,
} from "lucide-react";

import { Logo } from "@/components/layout/logo";
import { PlayerSearch } from "@/components/layout/player-search";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leaderboard", label: "Leaderboard", icon: ListOrdered },
  { href: "/players", label: "Players", icon: Users },
  { href: "/matches", label: "Matches", icon: History },
  { href: "/head-to-head", label: "Head-to-head", icon: GitCompare },
  { href: "/tournaments", label: "Tournaments", icon: Trophy },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/leaderboard") {
    return pathname === "/leaderboard" || pathname.startsWith("/leaderboard/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-card">
      <div className="mx-auto flex min-h-16 w-full max-w-[1120px] flex-wrap items-center gap-2 px-4 py-2 md:px-8">
        <Logo />
        <nav aria-label="Sections" className="hidden min-w-0 flex-1 flex-wrap items-center gap-1 md:flex">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-elevated text-primary"
                    : "text-muted-foreground hover:bg-elevated hover:text-foreground",
                )}
              >
                <Icon className="size-4" strokeWidth={1.75} aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto">
          <PlayerSearch />
        </div>
      </div>
    </header>
  );
}
