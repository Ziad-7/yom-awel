import { request, type Schema } from "./api/client";

// The API keeps the session in an HttpOnly cookie; the browser never sees the token.
export async function startSession() {
  await request<Schema["SessionResult"]>("/api/v1/auth/session", {
    method: "POST",
  });
}
export async function endSession() {
  await request<null>("/api/v1/auth/logout", { method: "POST" });
  sessionStorage.removeItem("yom-awel.pending");
}
