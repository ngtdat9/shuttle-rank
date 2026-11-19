"use client";

import type { ReactNode } from "react";

import { ErrorState } from "@/components/error-state";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiErrorMessage, isApiError } from "@/lib/admin/errors";
import { cn } from "@/lib/utils";

export const adminPrimaryButtonClass = "h-11 rounded-full px-4 md:h-10";
export const adminOutlineButtonClass = "h-11 rounded-full px-4 md:h-10";
export const adminDestructiveButtonClass =
  "h-11 rounded-full bg-destructive px-4 text-primary-foreground hover:bg-destructive/90 md:h-10";

export const adminSelectClass =
  "h-11 w-full rounded-xl border border-input bg-transparent px-3 text-sm text-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:opacity-50 md:h-10";

export const adminInputClass = "h-11 rounded-xl px-3 md:h-10";

export function AdminLiveError({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} role="alert" aria-live="assertive" className="text-sm text-negative">
      {children}
    </p>
  );
}

export function AdminField({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  error?: string | null;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      {children}
      {hint ? (
        <p id={`${htmlFor}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? <AdminLiveError id={`${htmlFor}-error`}>{error}</AdminLiveError> : null}
    </div>
  );
}

export function AdminDialogActions({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
      {children}
    </div>
  );
}

export function AdminFormDialog({
  open,
  onOpenChange,
  title,
  description,
  initialFocusId,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  initialFocusId?: string;
  children: ReactNode;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-h-[calc(100%-2rem)] max-w-[440px] overflow-y-auto rounded-[20px] bg-surface p-6 sm:max-w-[440px]"
        onOpenAutoFocus={(event) => {
          if (!initialFocusId) return;
          event.preventDefault();
          document.getElementById(initialFocusId)?.focus();
        }}
      >
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">{title}</DialogTitle>
          {description ? <DialogDescription>{description}</DialogDescription> : null}
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}

export function AdminBootSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="flex flex-col gap-4">
      <span className="sr-only">Checking admin session</span>
      <div className="h-8 w-40 animate-pulse rounded-full bg-elevated" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-[20px] bg-elevated" />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-[20px] bg-elevated" />
    </div>
  );
}

export function AdminQueryError({
  thing,
  error,
  onRetry,
}: {
  thing: string;
  error: unknown;
  onRetry: () => void;
}) {
  const network = isApiError(error) && error.status === 0;
  return (
    <ErrorState
      title={
        network ? "Couldn't reach Shuttle Rank. Try again." : `Couldn't load ${thing}.`
      }
      message={network ? "Check the connection and retry." : apiErrorMessage(error)}
      onRetry={onRetry}
      retryLabel="Retry"
    />
  );
}

export function describedBy(
  id: string,
  hint: boolean,
  error: boolean,
): string | undefined {
  const ids = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(
    Boolean,
  );
  return ids.length > 0 ? ids.join(" ") : undefined;
}

export function chipClass(className?: string) {
  return cn(
    "inline-flex h-5 items-center rounded-full px-2 text-xs font-medium",
    className,
  );
}
