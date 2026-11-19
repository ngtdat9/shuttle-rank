import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ErrorStateProps = {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
};

export function ErrorState({
  title = "Something went wrong",
  message = "This view could not be loaded.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-[22px] border border-border bg-card px-6 py-12 text-center",
        className,
      )}
    >
      <div className="grid size-10 place-items-center rounded-full bg-destructive/15 text-negative">
        <AlertTriangle className="size-4" aria-hidden />
      </div>
      <div className="max-w-sm">
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      </div>
      {onRetry ? (
        <Button type="button" variant="outline" className="rounded-full" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
