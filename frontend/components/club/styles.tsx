import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export const cardClass = "rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5";

export const heroCardClass = "rounded-[24px] bg-card p-4 ring-1 ring-foreground/10 md:p-5";

export const textActionClass =
  "inline-flex h-10 items-center text-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function QuietEmpty({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-sm text-muted-foreground", className)}>{children}</p>;
}
