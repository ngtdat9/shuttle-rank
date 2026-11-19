import Link from "next/link";

import { cn } from "@/lib/utils";

type LogoMarkProps = {
  className?: string;
};

/** Small shuttlecock mark: feather skirt over a cork. */
export function LogoMark({ className }: LogoMarkProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={cn("size-4", className)}
    >
      <path
        fill="currentColor"
        d="M4.6 3.4h14.8L15.6 12.6H8.4L4.6 3.4Z"
      />
      <path
        stroke="var(--primary)"
        strokeLinecap="round"
        strokeWidth="1.2"
        d="M8.5 4.3 9.6 11.6M12 3.7v8.1M15.5 4.3 14.4 11.6"
      />
      <circle cx="12" cy="17.6" r="2.9" fill="currentColor" />
    </svg>
  );
}

export function Logo() {
  return (
    <Link
      href="/"
      aria-label="Shuttle Rank"
      className="inline-flex shrink-0 items-center gap-2 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <span className="grid size-8 place-items-center rounded-full bg-primary text-primary-foreground">
        <LogoMark />
      </span>
      <span className="hidden text-sm font-semibold tracking-tight sm:inline">
        Shuttle Rank
      </span>
    </Link>
  );
}
