import type { ReactNode } from "react";

import { SiteFooter } from "@/components/layout/site-footer";
import { TopNav } from "@/components/layout/top-nav";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-6xl flex-col px-2 py-2 sm:px-4 sm:py-4">
      <div className="flex min-h-[calc(100dvh-1rem)] flex-1 flex-col overflow-hidden rounded-[20px] border border-border bg-background sm:min-h-[calc(100dvh-2rem)] sm:rounded-[28px]">
        <TopNav />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
        <SiteFooter />
      </div>
    </div>
  );
}
