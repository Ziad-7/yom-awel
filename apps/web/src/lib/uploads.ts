import { CSRF_HEADER, request, type Schema } from "./api/client";

export const MAX_BYTES = 5 * 1024 * 1024;
export function validateFile(file: Pick<File, "name" | "size">): string | null {
  if (!/\.(csv|xlsx)$/i.test(file.name)) return "اختار ملف CSV أو XLSX.";
  if (file.size === 0 || file.size > MAX_BYTES)
    return "حجم الملف لازم يكون من 1 بايت لحد 5 ميجابايت.";
  return null;
}
export async function uploadFile(file: File) {
  const error = validateFile(file);
  if (error) throw new Error(error);
  const digest = Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", await file.arrayBuffer()),
    ),
  )
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  const contentType = file.name.toLowerCase().endsWith(".csv")
    ? "text/csv"
    : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const auth = await request<Schema["UploadAuthorizationResult"]>(
    "/api/v1/artifacts/upload-authorization",
    {
      method: "POST",
      body: JSON.stringify({
        filename: file.name,
        size_bytes: file.size,
        artifact_sha256: digest,
        content_type: contentType,
      }),
    },
  );
  // The API only issues same-origin upload paths; anything else is refused.
  if (!auth.upload_url?.startsWith("/api/v1/artifacts/"))
    throw new Error("رابط الرفع غير صالح.");
  const response = await fetch(auth.upload_url, {
    method: "PUT",
    body: file,
    credentials: "same-origin",
    signal: AbortSignal.timeout(30000),
    headers: {
      "Content-Type": contentType,
      ...CSRF_HEADER,
      ...auth.headers,
    },
  });
  if (!response.ok) throw new Error("الرفع ماكملش. اختار الملف وحاول تاني.");
  await request<Schema["UploadCompletionResult"]>(
    `/api/v1/artifacts/${auth.artifact_id}/complete`,
    { method: "POST" },
  );
  return { artifact_id: auth.artifact_id, artifact_sha256: digest };
}
