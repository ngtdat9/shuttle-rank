import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export const cardClass = "sr-panel rounded-[24px] p-4 md:p-6";

export const heroCardClass = "sr-panel rounded-[28px] p-5 md:p-8";

export const textActionClass =
  "sr-action inline-flex h-10 items-center text-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function QuietEmpty({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-sm text-muted-foreground", className)}>{children}</p>;
}
