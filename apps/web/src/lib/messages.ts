import { ApiError } from "./api/client";
import type { Dictionary } from "./i18n/en";
import { isRejectionCode, type RejectionCode } from "./i18n/keys";

/** Transport error codes that describe the uploaded file itself. */
const FILE_ERRORS: Record<string, RejectionCode> = {
  too_large: "artifact_too_large",
  unsupported_artifact: "unsupported_type",
  artifact_type_mismatch: "mime_mismatch",
  unsafe_artifact: "artifact_unreadable",
  invalid_artifact: "artifact_unreadable",
};

export function rejectionCodeOf(code: string): RejectionCode | null {
  if (isRejectionCode(code)) return code;
  return FILE_ERRORS[code] ?? null;
}

export function rejectionMessage(t: Dictionary, code: string): string {
  const known = rejectionCodeOf(code);
  return known ? t.rejections[known] : t.rejections.unknown;
}

/** Maps any failure to safe, translated copy; server text and stack traces never reach the UI. */
export function errorMessage(t: Dictionary, cause: unknown): string {
  if (!(cause instanceof ApiError)) return t.errors.generic;
  const rejection = rejectionCodeOf(cause.code);
  if (rejection) return t.rejections[rejection];
  if (cause.code === "offline") return t.errors.offline;
  if (cause.status === 401) return t.errors.session;
  if (cause.status >= 500) return t.errors.service;
  return t.errors.generic;
}
