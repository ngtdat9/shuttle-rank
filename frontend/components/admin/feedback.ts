"use client";

import { toast } from "sonner";

import { apiErrorMessage } from "@/lib/admin/errors";

export function notifySuccess(message: string) {
  toast.success(message);
}

export function notifyFailure(error: unknown): string {
  const message = apiErrorMessage(error);
  toast.error(message);
  return message;
}
