export const API_BASE = "/api/v1";
export const CSRF_HEADER = { "X-Yom-Awel": "1" } as const;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(code);
  }
}

const isSafeMethod = (method: string) => method === "GET" || method === "HEAD";

/** Builds the headers for a same-origin API call; every state change carries the CSRF guard. */
export function apiHeaders(init: RequestInit): HeadersInit {
  const method = (init.method ?? "GET").toUpperCase();
  return {
    ...(typeof init.body === "string" ? { "Content-Type": "application/json" } : {}),
    ...(isSafeMethod(method) ? {} : CSRF_HEADER),
    ...init.headers,
  };
}

async function errorCode(response: Response): Promise<string> {
  const body: unknown = await response.json().catch(() => null);
  if (body && typeof body === "object" && "code" in body && typeof body.code === "string")
    return body.code;
  return "unavailable";
}

export async function send(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith("/") || path.startsWith("//")) throw new ApiError(0, "invalid_path");
  let response: Response;
  try {
    response = await fetch(API_BASE + path, {
      ...init,
      cache: "no-store",
      credentials: "same-origin",
      signal: init.signal ?? AbortSignal.timeout(30000),
      headers: apiHeaders(init),
    });
  } catch {
    throw new ApiError(0, "offline");
  }
  if (!response.ok) throw new ApiError(response.status, await errorCode(response));
  return response;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await send(path, init);
  return (await response.json()) as T;
}
