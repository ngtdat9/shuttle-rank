import type { Metadata } from "next";

import { DesignShowcase } from "./showcase";

/**
 * Component showcase for the Shuttle Rank design system.
 * Dev-only review page. Do not link this route from navigation.
 */
export const metadata: Metadata = {
  title: "Design system",
  robots: { index: false, follow: false },
};

export default function DesignSystemPage() {
  return <DesignShowcase />;
}
