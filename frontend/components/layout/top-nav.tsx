"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowLeftRight,
  CalendarDays,
  CircleDot,
  LayoutGrid,
  Medal,
  Menu,
  Trophy,
  Users,
  type LucideIcon,
} from "lucide-react";

import { Logo } from "@/components/layout/logo";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutGrid },
  { href: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { href: "/players", label: "Players", icon: Users },
  { href: "/matches", label: "Matches", icon: CircleDot },
  { href: "/head-to-head", label: "Head-to-Head", icon: ArrowLeftRight },
  { href: "/tournaments", label: "Tournaments", icon: Medal },
  { href: "/leaderboard/monthly", label: "Monthly", icon: CalendarDays },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  if (href === "/leaderboard") {
    return (
      pathname === "/leaderboard" ||
      (pathname.startsWith("/leaderboard/") &&
        !pathname.startsWith("/leaderboard/monthly"))
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function navClass(active: boolean, compact = false) {
  return cn(
    "inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    compact ? "px-2.5 py-1.5 text-xs" : "px-3 py-2.5 text-sm",
    active
      ? "bg-primary text-primary-foreground"
      : "text-muted-foreground hover:bg-elevated hover:text-foreground",
  );
}

export function TopNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const adminActive = pathname.startsWith("/admin");

  return (
    <header className="flex items-center gap-2 border-b border-border px-3 py-3 sm:gap-3 sm:px-5">
      <Logo />

      <nav
        aria-label="Primary"
        className="hidden min-w-0 flex-1 items-center gap-1 overflow-x-auto lg:flex lg:justify-center [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={navClass(active, true)}
            >
              <Icon className="size-3.5" aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
        <Link
          href="/admin"
          aria-current={adminActive ? "page" : undefined}
          className={cn(
            "rounded-full px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            adminActive
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:bg-elevated hover:text-foreground",
          )}
        >
          Admin
        </Link>

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="rounded-full lg:hidden"
              aria-label="Open menu"
            >
              <Menu />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-full bg-card sm:max-w-sm">
            <SheetHeader>
              <SheetTitle>Shuttle Rank</SheetTitle>
              <SheetDescription>Club pages</SheetDescription>
            </SheetHeader>
            <nav aria-label="Mobile" className="flex flex-col gap-1 px-4">
              {NAV_ITEMS.map((item) => {
                const active = isActive(pathname, item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={navClass(active)}
                    onClick={() => setOpen(false)}
                  >
                    <Icon className="size-4" aria-hidden />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
