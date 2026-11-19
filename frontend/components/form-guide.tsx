import { cn } from "@/lib/utils";

export type FormResult = "W" | "L";

type FormGuideProps = {
  results: FormResult[];
  className?: string;
};

export function FormGuide({ results, className }: FormGuideProps) {
  const summary = results.length === 0 ? "No recent results" : `Form ${results.join(" ")}`;

  return (
    <div className={cn("flex items-center gap-1", className)} aria-label={summary}>
      {results.length === 0 ? (
        <span className="text-xs text-muted-foreground">—</span>
      ) : (
        results.map((result, index) => (
          <span
            key={`${result}-${index}`}
            aria-hidden
            className={cn(
              "inline-flex size-6 items-center justify-center rounded-full text-[10px] font-semibold",
              result === "W"
                ? "bg-primary/15 text-positive"
                : "bg-destructive/15 text-negative",
            )}
          >
            {result}
          </span>
        ))
      )}
    </div>
  );
}
