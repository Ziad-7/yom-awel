import type { components } from "./generated";
export type Schema = components["schemas"];
export const API = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");
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
  token: string | null,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(API + path, {
    ...init,
    cache: "no-store",
    signal: init.signal ?? AbortSignal.timeout(25000),
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...init.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      response.status,
      body?.code || "unavailable",
      body?.message || "الخدمة مش متاحة دلوقتي. حاول تاني.",
    );
  return body as T;
}
export async function downloadSample(token: string, clean = false) {
  const response = await fetch(API + "/api/v1/tasks/sample?clean=" + clean, {
    headers: { Authorization: "Bearer " + token },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error("تعذّر تحميل الملف.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = clean ? "sales-demo-clean.csv" : "sales-demo.csv";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
