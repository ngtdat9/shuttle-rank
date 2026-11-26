"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Ellipsis,
  GitCompare,
  History,
  LayoutDashboard,
  ListOrdered,
  Trophy,
  Users,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

const TABS: NavItem[] = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/leaderboard", label: "Ranks", icon: ListOrdered },
  { href: "/players", label: "Players", icon: Users },
  { href: "/matches", label: "Matches", icon: History },
];

const MORE: NavItem[] = [
  { href: "/head-to-head", label: "Head-to-head", icon: GitCompare },
  { href: "/tournaments", label: "Tournaments", icon: Trophy },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

const tabClass =
  "sr-tab flex h-[52px] min-w-14 flex-col items-center justify-center gap-0.5 rounded-[18px] px-2 text-[11px] font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function BottomNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLLIElement>(null);
  const moreActive = MORE.some((item) => isActive(pathname, item.href));

  useEffect(() => {
    if (!moreOpen) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setMoreOpen(false);
    }
    function onPointer(event: PointerEvent) {
      if (moreRef.current && !moreRef.current.contains(event.target as Node)) {
        setMoreOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [moreOpen]);

  return (
    <nav
      aria-label="Primary"
      className="glass glass-open fixed inset-x-3 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-40 rounded-[28px] md:hidden"
    >
      <ul className="flex h-[68px] items-center justify-around px-2">
        {TABS.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  tabClass,
                  active
                    ? "bg-primary/20 text-[#d4ffb0] shadow-[inset_0_0_0_1px_rgba(166,243,107,0.4)]"
                    : "text-foreground/80",
                )}
              >
                <Icon className="size-5" strokeWidth={2} aria-hidden />
                {item.label}
              </Link>
            </li>
          );
        })}
        <li className="relative" ref={moreRef}>
          <button
            type="button"
            aria-expanded={moreOpen}
            aria-haspopup="true"
            aria-controls="more-menu"
            className={cn(
              tabClass,
              moreActive || moreOpen
                ? "bg-primary/20 text-[#d4ffb0] shadow-[inset_0_0_0_1px_rgba(166,243,107,0.4)]"
                : "text-foreground/80",
            )}
            onClick={() => setMoreOpen((open) => !open)}
          >
            <Ellipsis className="size-5" strokeWidth={2} aria-hidden />
            More
          </button>
          {moreOpen ? (
            <ul
              id="more-menu"
              className="absolute right-0 bottom-[calc(100%+0.75rem)] w-56 rounded-[22px] border border-white/20 bg-[rgba(8,28,17,0.95)] p-2 shadow-[0_24px_60px_-12px_rgba(0,12,6,0.7)] backdrop-blur-xl"
            >
              {MORE.map((item) => {
                const Icon = item.icon;
                const active = isActive(pathname, item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex min-h-12 items-center gap-3 rounded-full px-4 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        active ? "bg-primary/20 text-[#d4ffb0]" : "text-foreground hover:bg-white/10",
                      )}
                      onClick={() => setMoreOpen(false)}
                    >
                      <Icon className="size-4" aria-hidden />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </li>
      </ul>
    </nav>
  );
}
