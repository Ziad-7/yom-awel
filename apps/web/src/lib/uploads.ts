import { API, request, type Schema } from "./api/client";

export const MAX_BYTES = 5 * 1024 * 1024;
export function validateFile(file: Pick<File, "name" | "size">): string | null {
  if (!/\.(csv|xlsx)$/i.test(file.name)) return "اختار ملف CSV أو XLSX.";
  if (file.size === 0 || file.size > MAX_BYTES)
    return "حجم الملف لازم يكون من 1 بايت لحد 5 ميجابايت.";
  return null;
}
export async function uploadFile(file: File, token: string) {
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
    token,
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
  if (!auth.upload_url) throw new Error("رابط الرفع مش متاح.");
  const local =
    auth.upload_url.startsWith("/") && !auth.upload_url.startsWith("//");
  const target = new URL(auth.upload_url, API);
  const allowedStorage = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (
    !local &&
    (!allowedStorage ||
      target.origin !== new URL(allowedStorage).origin ||
      target.protocol !== "https:")
  )
    throw new Error("رابط الرفع غير صالح.");
  const response = await fetch(local ? API + auth.upload_url : target.href, {
    method: "PUT",
    body: file,
    signal: AbortSignal.timeout(30000),
    headers: {
      "Content-Type": contentType,
      ...(local ? { Authorization: "Bearer " + token } : {}),
      ...auth.headers,
    },
  });
  if (!response.ok) throw new Error("الرفع ماكملش. اختار الملف وحاول تاني.");
  await request<Schema["UploadCompletionResult"]>(
    `/api/v1/artifacts/${auth.artifact_id}/complete`,
    token,
    { method: "POST" },
  );
  return { artifact_id: auth.artifact_id, artifact_sha256: digest };
}
