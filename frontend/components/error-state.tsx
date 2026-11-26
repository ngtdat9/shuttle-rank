import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ErrorStateProps = {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
};

export function ErrorState({
  title = "Something went wrong",
  message = "This view could not be loaded.",
  onRetry,
  retryLabel = "Try again",
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "sr-panel flex flex-col items-start gap-3 rounded-[24px] border border-border border-l-[3px] border-l-destructive bg-card px-5 py-6 text-left",
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
        <Button type="button" variant="outline" className="h-10 rounded-full px-4" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
