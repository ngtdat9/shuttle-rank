import { LogoMark } from "@/components/layout/logo";
import { Card, CardContent } from "@/components/ui/card";

function CourtLines() {
  return (
    <svg
      viewBox="0 0 320 200"
      className="h-full w-full text-foreground/20"
      fill="none"
      aria-hidden="true"
    >
      <rect
        x="18"
        y="16"
        width="284"
        height="168"
        rx="10"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <line x1="160" y1="16" x2="160" y2="184" stroke="currentColor" strokeWidth="1.5" />
      <line x1="18" y1="100" x2="302" y2="100" stroke="currentColor" strokeWidth="1.5" />
      <rect x="92" y="56" width="136" height="88" stroke="currentColor" strokeWidth="1.5" />
      <line x1="160" y1="56" x2="160" y2="144" stroke="#a6f36b" strokeWidth="2" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <Card className="overflow-hidden rounded-[22px] bg-elevated ring-foreground/10">
      <CardContent className="grid gap-8 py-2 sm:py-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(220px,0.8fr)] lg:items-center">
        <div className="max-w-xl">
          <div className="grid size-12 place-items-center rounded-full bg-primary text-primary-foreground">
            <LogoMark className="size-6" />
          </div>
          <p className="mt-6 text-xs font-medium tracking-[0.16em] text-primary uppercase">
            Men&apos;s singles
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            The dashboard is coming
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Shuttle Rank will be the club&apos;s public home for Elo ratings, recent
            matches, and head-to-head records. This page stays empty of numbers until
            they arrive from the API.
          </p>
        </div>
        <div className="overflow-hidden rounded-[20px] border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Court</p>
          <div className="mt-3 aspect-[16/10]">
            <CourtLines />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
