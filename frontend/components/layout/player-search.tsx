"use client";

import { useId, useRef, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { getPlayers } from "@/lib/api/client";
import { formatRating } from "@/lib/format";
import type { PlayerListItem } from "@/types/api";

export function PlayerSearch() {
  const router = useRouter();
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState<PlayerListItem[] | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [active, setActive] = useState(0);
  const loading = useRef(false);

  function ensurePlayers() {
    if (players || loading.current) return;
    loading.current = true;
    setStatus("loading");
    getPlayers()
      .then((response) => {
        setPlayers(response.items);
        setStatus("ready");
      })
      .catch(() => {
        loading.current = false;
        setStatus("error");
      });
  }

  function openSearch() {
    setOpen(true);
    ensurePlayers();
  }

  const filtered = (players ?? []).filter((player) =>
    player.display_name.toLowerCase().includes(query.trim().toLowerCase()),
  );
  const current = filtered[Math.min(active, Math.max(filtered.length - 1, 0))];

  function choose(id: string) {
    setOpen(false);
    setQuery("");
    router.push(`/players/${id}`);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((index) => Math.min(index + 1, Math.max(filtered.length - 1, 0)));
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    }
    if (event.key === "Enter" && current) {
      event.preventDefault();
      choose(current.id);
    }
  }

  return (
    <div className="relative">
      <label className="sr-only" htmlFor={`${listId}-input`}>
        Search players
      </label>
      <div className="flex items-center">
        <Search className="pointer-events-none absolute left-3.5 size-4 text-foreground/75 md:left-4" aria-hidden />
        <input
          id={`${listId}-input`}
          ref={inputRef}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && current ? `${listId}-${current.id}` : undefined}
          value={query}
          placeholder="Search players"
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
            openSearch();
          }}
          onFocus={openSearch}
          onKeyDown={onKeyDown}
          className="h-11 w-11 rounded-full border border-white/20 pr-3 pl-10 text-sm font-medium text-foreground placeholder:text-transparent focus-visible:w-52 focus-visible:placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:w-44 md:placeholder:text-muted-foreground xl:w-56"
        />
      </div>
      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute top-14 right-0 z-40 max-h-80 w-72 max-w-[calc(100vw-1.5rem)] overflow-auto rounded-[20px] border border-white/20 bg-[rgba(8,28,17,0.94)] p-1.5 shadow-[0_24px_60px_-12px_rgba(0,12,6,0.7)] backdrop-blur-xl"
        >
          {status === "loading" ? <li className="px-3 py-2 text-sm text-muted-foreground">Loading players…</li> : null}
          {status === "error" ? (
            <li className="px-3 py-2 text-sm text-muted-foreground">
              Couldn&apos;t load players.{" "}
              <button
                type="button"
                className="underline"
                onClick={() => {
                  loading.current = false;
                  setPlayers(null);
                  setStatus("idle");
                  ensurePlayers();
                }}
              >
                Retry
              </button>
            </li>
          ) : null}
          {status === "ready" && filtered.length === 0 ? (
            <li className="px-3 py-2 text-sm text-muted-foreground">No player found.</li>
          ) : null}
          {filtered.map((player) => (
            <li key={player.id} role="presentation">
              <button
                id={`${listId}-${player.id}`}
                type="button"
                role="option"
                aria-selected={current?.id === player.id}
                className="flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left text-sm min-h-11 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-selected:bg-white/15"
                onMouseEnter={() => setActive(filtered.findIndex((item) => item.id === player.id))}
                onClick={() => choose(player.id)}
              >
                <span className="truncate">{player.display_name}</span>
                <span className="font-mono text-muted-foreground tabular-nums">
                  {formatRating(player.current_rating)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
