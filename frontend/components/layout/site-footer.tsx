import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex w-full max-w-[1120px] items-center justify-between gap-3 px-4 py-4 text-xs text-muted-foreground md:px-8">
        <p>Men&apos;s singles · Elo</p>
        <Link
          href="/admin"
          className="rounded-full underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Admin
        </Link>
      </div>
    </footer>
  );
}
