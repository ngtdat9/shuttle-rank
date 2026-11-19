"use client";

import type { ReactNode } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  destructive?: boolean;
  pending?: boolean;
  error?: string | null;
};

/**
 * Confirmation for destructive or rating-affecting admin actions.
 * Stays open until the parent sets `open` to false, so a failed action can remain on screen.
 * Initial focus is Cancel. Enter never confirms.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  destructive = false,
  pending = false,
  error = null,
}: ConfirmDialogProps) {
  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        if (pending) return;
        onOpenChange(next);
      }}
    >
      <AlertDialogContent
        className="max-w-[440px] rounded-[20px] bg-surface p-6 sm:max-w-[440px]"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          const content = event.currentTarget;
          if (!(content instanceof HTMLElement)) return;
          content
            .querySelector<HTMLElement>("[data-slot=alert-dialog-cancel]")
            ?.focus();
        }}
        onKeyDownCapture={(event) => {
          if (event.key !== "Enter") return;
          const target = event.target;
          if (!(target instanceof HTMLElement)) return;
          if (target.closest("[data-slot=alert-dialog-cancel]")) return;
          event.preventDefault();
          event.stopPropagation();
        }}
      >
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        {error ? (
          <p role="alert" aria-live="assertive" className="text-sm text-negative">
            {error}
          </p>
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel
            disabled={pending}
            className="h-11 rounded-full px-4 md:h-10"
          >
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            variant={destructive ? "destructive" : "default"}
            className={
              destructive
                ? "h-11 rounded-full bg-destructive px-4 text-primary-foreground hover:bg-destructive/90 md:h-10"
                : "h-11 rounded-full px-4 md:h-10"
            }
            disabled={pending}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
          >
            {pending ? "Working…" : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
