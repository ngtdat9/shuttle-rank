import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

import { cn } from "@/lib/utils";

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
};

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "sr-dashed flex flex-col items-center justify-center gap-3 rounded-[24px] border border-dashed border-border px-6 py-12 text-center",
        className,
      )}
    >
      <div className="grid size-10 place-items-center rounded-full bg-elevated text-muted-foreground">
        {icon ?? <Inbox className="size-4" aria-hidden />}
      </div>
      <div className="max-w-sm">
        <p className="text-sm font-medium">{title}</p>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
