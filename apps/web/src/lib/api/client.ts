import type { components } from "./generated";
export type Schema = components["schemas"];
// Same-origin: next.config.ts proxies /api/* to the API, so the session cookie is first-party.
export const CSRF_HEADER = { "X-Yom-Awel": "1" };
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const response = await fetch(path, {
    ...init,
    cache: "no-store",
    credentials: "same-origin",
    signal: init.signal ?? AbortSignal.timeout(25000),
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(method === "GET" ? {} : CSRF_HEADER),
      ...init.headers,
    },
  });
  const body =
    response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      response.status,
      body?.code || "unavailable",
      body?.message || "الخدمة مش متاحة دلوقتي. حاول تاني.",
    );
  return body as T;
}
export async function downloadDataset(taskId: string, format: "csv" | "xlsx") {
  const response = await fetch(
    `/api/v1/tasks/${encodeURIComponent(taskId)}/dataset?format=${format}`,
    { credentials: "same-origin", signal: AbortSignal.timeout(15000) },
  );
  if (!response.ok) throw new Error("تعذّر تحميل الملف.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `sales_dirty.${format}`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
