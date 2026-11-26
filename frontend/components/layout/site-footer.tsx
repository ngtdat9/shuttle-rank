import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="pb-[calc(6.5rem+env(safe-area-inset-bottom))] md:pb-0">
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-2 px-4 py-4 text-xs text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6 xl:px-8">
        <p>
          Men&apos;s singles · Elo ·{" "}
          <a
            href="https://unsplash.com/photos/a-badminton-racket-and-two-shuttles-on-a-green-surface-VRqmHMYMq1c"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full underline underline-offset-4 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Background photo by Allison Saeng on Unsplash
          </a>
        </p>
        <Link
          href="/admin"
          className="inline-flex h-10 items-center rounded-full underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-auto"
        >
          Admin
        </Link>
      </div>
    </footer>
  );
}
