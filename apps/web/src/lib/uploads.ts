import { API_BASE, ApiError, request, send } from "./api/client";
import type { UploadAuthorization, UploadCompletion } from "./api/contract";
import type { RejectionCode } from "./i18n/keys";

export const MAX_BYTES = 5 * 1024 * 1024;
const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const ZIP_MAGIC = [0x50, 0x4b, 0x03, 0x04];

type Candidate = Pick<File, "name" | "size">;
export type UploadedArtifact = { artifact_id: string; artifact_sha256: string };

export const extensionOf = (name: string) => name.toLowerCase().match(/\.(csv|xlsx)$/)?.[1];

/** Client-side checks mirror the server boundary; the API stays authoritative. */
export function validateFile(file: Candidate, maxBytes = MAX_BYTES): RejectionCode | null {
  if (!extensionOf(file.name)) return "unsupported_type";
  if (file.size === 0) return "empty_file";
  if (file.size > maxBytes) return "artifact_too_large";
  return null;
}

/** An .xlsx workbook is a zip archive; anything else under that name is rejected early. */
export function validateSignature(name: string, head: Uint8Array): RejectionCode | null {
  if (extensionOf(name) !== "xlsx") return null;
  return ZIP_MAGIC.every((byte, index) => head[index] === byte) ? null : "mime_mismatch";
}

export async function inspectFile(file: File, maxBytes = MAX_BYTES): Promise<RejectionCode | null> {
  const invalid = validateFile(file, maxBytes);
  if (invalid) return invalid;
  const head = new Uint8Array(await file.slice(0, ZIP_MAGIC.length).arrayBuffer());
  return validateSignature(file.name, head);
}

export const contentTypeOf = (name: string) =>
  extensionOf(name) === "csv" ? "text/csv" : XLSX_TYPE;

async function sha256(file: File) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Upload URLs must stay on this origin, under the API proxy. */
export function uploadPath(url: string | null | undefined): string {
  if (!url || !url.startsWith(API_BASE + "/") || /\/\/|\.\./.test(url))
    throw new ApiError(0, "invalid_upload_url");
  return url.slice(API_BASE.length);
}

export async function uploadFile(file: File): Promise<UploadedArtifact> {
  const invalid = await inspectFile(file);
  if (invalid) throw new ApiError(0, invalid);
  const digest = await sha256(file);
  const contentType = contentTypeOf(file.name);
  const auth = await request<UploadAuthorization>("/artifacts/upload-authorization", {
    method: "POST",
    body: JSON.stringify({
      filename: file.name,
      size_bytes: file.size,
      artifact_sha256: digest,
      content_type: contentType,
    }),
  });
  await send(uploadPath(auth.upload_url), {
    method: "PUT",
    body: file,
    signal: AbortSignal.timeout(60000),
    headers: { ...auth.headers, "Content-Type": contentType },
  });
  await request<UploadCompletion>(
    `/artifacts/${encodeURIComponent(auth.artifact_id)}/complete`,
    { method: "POST" },
  );
  return { artifact_id: auth.artifact_id, artifact_sha256: digest };
}
