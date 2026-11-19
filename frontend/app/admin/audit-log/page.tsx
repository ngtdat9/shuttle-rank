import { Suspense } from "react";

import { AuditLogView } from "@/components/admin/audit-log-view";

export const metadata = { title: "Audit log" };

export default function AdminAuditLogPage() {
  return (
    <Suspense
      fallback={
        <div
          className="h-40 animate-pulse rounded-[20px] bg-elevated"
          aria-busy="true"
        />
      }
    >
      <AuditLogView />
    </Suspense>
  );
}
