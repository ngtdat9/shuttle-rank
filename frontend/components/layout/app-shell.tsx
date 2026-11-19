import type { ReactNode } from "react";

import { BottomNav } from "@/components/layout/bottom-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { TopNav } from "@/components/layout/top-nav";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-full flex-col pb-16 md:pb-0">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-full focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <TopNav />
      <main id="content" className="mx-auto w-full max-w-[1120px] flex-1 px-4 py-6 md:px-8 md:py-8">
        {children}
      </main>
      <SiteFooter />
      <BottomNav />
    </div>
  );
}
