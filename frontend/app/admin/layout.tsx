"use client";

import { AdminFrame } from "@/components/admin/shell";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminFrame>{children}</AdminFrame>;
}
