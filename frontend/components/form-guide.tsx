import { cn } from "@/lib/utils";

export type FormResult = "W" | "L";

type FormGuideProps = {
  results: FormResult[];
  /**
   * API `recent_form` is newest-first. Pass "newest-first" to paint
   * oldest on the left and newest on the right.
   */
  order?: "as-given" | "newest-first";
  className?: string;
};

export function FormGuide({ results, order = "as-given", className }: FormGuideProps) {
  const display = order === "newest-first" ? [...results].reverse() : results;
  const summary =
    display.length === 0
      ? "No recent results"
      : `Form, oldest to newest: ${display.join(" ")}`;

  return (
    <div className={cn("flex items-center gap-1", className)} aria-label={summary}>
      {display.length === 0 ? (
        <span className="text-xs text-muted-foreground">—</span>
      ) : (
        display.map((result, index) => (
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
