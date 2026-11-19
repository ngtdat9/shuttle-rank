import { cn } from "@/lib/utils";

export type StatusKind =
  | "completed"
  | "canceled"
  | "disputed"
  | "draft"
  | "in_progress";

type StatusBadgeProps = {
  status: StatusKind;
  className?: string;
};

const STATUS: Record<StatusKind, { label: string; className: string }> = {
  completed: {
    label: "Completed",
    className: "bg-primary/15 text-positive",
  },
  canceled: {
    label: "Canceled",
    className: "bg-muted text-muted-foreground",
  },
  disputed: {
    label: "Disputed",
    className: "bg-warning/15 text-warning",
  },
  draft: {
    label: "Draft",
    className: "bg-foreground/8 text-muted-foreground",
  },
  in_progress: {
    label: "In progress",
    className: "bg-secondary/15 text-secondary",
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const item = STATUS[status];

  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full px-2 text-xs font-medium",
        item.className,
        className,
      )}
    >
      {item.label}
    </span>
  );
}
