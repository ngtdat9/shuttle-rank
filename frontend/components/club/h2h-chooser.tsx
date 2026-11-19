"use client";

import { Button } from "@/components/ui/button";
import { InactiveBadge } from "@/components/inactive-badge";
import { fieldLabelClass, nativeSelectClass, useQueryUpdate } from "@/components/club/query-controls";
import { formatRating } from "@/lib/format";
import type { PlayerListItem } from "@/types/api";

function optionLabel(player: PlayerListItem): string {
  const inactive = player.is_active ? "" : " · Inactive";
  return `${player.display_name} · ${formatRating(player.current_rating)}${inactive}`;
}

export function HeadToHeadChooser({ players }: { players: PlayerListItem[] }) {
  const { searchParams, update } = useQueryUpdate();
  const a = searchParams.get("a") ?? "";
  const b = searchParams.get("b") ?? "";
  const selectedA = players.find((player) => player.id === a);
  const selectedB = players.find((player) => player.id === b);

  return (
    <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-end">
      <PlayerSelect
        label="Player A"
        value={a}
        players={players}
        onChange={(value) => update({ a: value })}
        inactive={selectedA ? !selectedA.is_active : false}
      />
      <Button
        type="button"
        variant="outline"
        className="h-11 px-4 md:h-10"
        onClick={() => update({ a: b || null, b: a || null })}
      >
        Swap
      </Button>
      <PlayerSelect
        label="Player B"
        value={b}
        players={players}
        onChange={(value) => update({ b: value })}
        inactive={selectedB ? !selectedB.is_active : false}
      />
    </div>
  );
}

function PlayerSelect({
  label,
  value,
  players,
  onChange,
  inactive,
}: {
  label: string;
  value: string;
  players: PlayerListItem[];
  onChange: (value: string | null) => void;
  inactive: boolean;
}) {
  return (
    <label className={fieldLabelClass}>
      <span className="flex items-center gap-2">
        {label}
        {inactive ? <InactiveBadge /> : null}
      </span>
      <select
        className={nativeSelectClass}
        value={players.some((player) => player.id === value) ? value : ""}
        onChange={(event) => onChange(event.target.value || null)}
      >
        <option value="">Select a player</option>
        {players.map((player) => (
          <option key={player.id} value={player.id}>
            {optionLabel(player)}
          </option>
        ))}
      </select>
    </label>
  );
}
