import { cn } from "@/lib/utils";

export function InactiveBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full bg-foreground/8 px-2 text-xs font-medium text-muted-foreground",
        className,
      )}
    >
      Inactive
    </span>
  );
}
