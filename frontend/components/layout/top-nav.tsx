"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/layout/logo";
import { PlayerSearch } from "@/components/layout/player-search";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/players", label: "Players" },
  { href: "/matches", label: "Matches" },
  { href: "/head-to-head", label: "Head-to-head" },
  { href: "/tournaments", label: "Tournaments" },
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
    <div className="sticky top-0 z-30 mx-auto w-full max-w-[1280px] px-3 pt-3 md:px-6 md:pt-5 xl:px-8">
      <header className="glass glass-open flex w-full items-center gap-2 rounded-full p-2 pl-4 md:gap-3">
        <Logo />
        <nav aria-label="Sections" className="hidden min-w-0 flex-1 flex-nowrap items-center gap-0.5 md:flex">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex h-10 items-center whitespace-nowrap rounded-full px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring xl:px-4",
                  active
                    ? "bg-primary text-primary-foreground shadow-[0_6px_20px_-6px_rgba(166,243,107,0.7),inset_0_1px_0_rgba(255,255,255,0.6)]"
                    : "text-foreground/85 hover:bg-white/10 hover:text-white",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto">
          <PlayerSearch />
        </div>
      </header>
    </div>
  );
}
