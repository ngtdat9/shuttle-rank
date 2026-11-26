"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import { usePathname } from "next/navigation";

import { BottomNav } from "@/components/layout/bottom-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { TopNav } from "@/components/layout/top-nav";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  if (pathname.startsWith("/admin")) {
    return <>{children}</>;
  }

  return (
    <div className="sr-public flex min-h-full flex-col">
      <div className="sr-bg" aria-hidden="true">
        <Image
          src="/images/court-bg.jpg"
          alt=""
          fill
          priority
          sizes="100vw"
          quality={70}
          className="object-cover object-[58%_40%]"
        />
      </div>
      <div className="sr-scrim" aria-hidden="true" />
      <div className="relative z-10 flex min-h-full flex-1 flex-col">
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-full focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
        >
          Skip to content
        </a>
        <TopNav />
        <main
          id="content"
          className="mx-auto w-full max-w-[1280px] flex-1 px-4 pt-5 pb-6 md:px-6 md:pt-6 md:pb-8 xl:px-8"
        >
          {children}
        </main>
        <SiteFooter />
        <BottomNav />
      </div>
    </div>
  );
}
