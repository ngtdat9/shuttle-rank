"use client";

import type { ScoreRow } from "@/lib/admin/form";
import { adminInputClass } from "@/components/admin/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ScoresEditor({
  rows,
  onChange,
  playerAName,
  playerBName,
  idPrefix,
}: {
  rows: ScoreRow[];
  onChange: (rows: ScoreRow[]) => void;
  playerAName: string;
  playerBName: string;
  idPrefix: string;
}) {
  function update(index: number, side: "a" | "b", value: string) {
    onChange(
      rows.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [side]: value } : row,
      ),
    );
  }

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-xs font-medium text-muted-foreground">Game scores</legend>
      <p className="text-xs text-muted-foreground">
        Scores are {playerAName || "player A"} first. They do not change Elo.
      </p>
      {rows.map((row, index) => (
        <div key={`${idPrefix}-${index}`} className="flex items-end gap-2">
          <div className="flex flex-1 flex-col gap-1">
            <label
              htmlFor={`${idPrefix}-a-${index}`}
              className="text-xs text-muted-foreground"
            >
              Game {index + 1}, {playerAName || "A"}
            </label>
            <Input
              id={`${idPrefix}-a-${index}`}
              className={adminInputClass}
              inputMode="numeric"
              min={0}
              max={99}
              value={row.a}
              onChange={(event) => update(index, "a", event.target.value)}
            />
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label
              htmlFor={`${idPrefix}-b-${index}`}
              className="text-xs text-muted-foreground"
            >
              Game {index + 1}, {playerBName || "B"}
            </label>
            <Input
              id={`${idPrefix}-b-${index}`}
              className={adminInputClass}
              inputMode="numeric"
              min={0}
              max={99}
              value={row.b}
              onChange={(event) => update(index, "b", event.target.value)}
            />
          </div>
          <Button
            type="button"
            variant="outline"
            className="h-11 rounded-full px-3 md:h-10"
            onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}
          >
            Remove
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        className="h-11 w-fit rounded-full px-4 md:h-10"
        disabled={rows.length >= 5}
        onClick={() => onChange([...rows, { a: "", b: "" }])}
      >
        Add game
      </Button>
    </fieldset>
  );
}
