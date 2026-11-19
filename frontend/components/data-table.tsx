import type { ComponentProps } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export const dataTableIconButtonClass =
  "inline-flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function DataTable({
  className,
  containerClassName,
  ...props
}: ComponentProps<"table"> & { containerClassName?: string }) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-[22px] bg-card ring-1 ring-foreground/10",
        containerClassName,
      )}
    >
      <Table className={cn("text-sm", className)} {...props} />
    </div>
  );
}

export function DataTableHeader({ className, ...props }: ComponentProps<"thead">) {
  return <TableHeader className={cn("bg-elevated/60", className)} {...props} />;
}

export function DataTableBody({ className, ...props }: ComponentProps<"tbody">) {
  return <TableBody className={className} {...props} />;
}

export function DataTableRow({ className, ...props }: ComponentProps<"tr">) {
  return (
    <TableRow
      className={cn("border-border hover:bg-elevated/50", className)}
      {...props}
    />
  );
}

export function DataTableHead({ className, ...props }: ComponentProps<"th">) {
  return (
    <TableHead
      className={cn(
        "h-10 px-3 text-[11px] font-medium tracking-wide text-muted-foreground uppercase",
        className,
      )}
      {...props}
    />
  );
}

export function DataTableCell({ className, ...props }: ComponentProps<"td">) {
  return <TableCell className={cn("px-3 py-3", className)} {...props} />;
}
