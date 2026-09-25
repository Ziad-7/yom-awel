import type { NextConfig } from "next";

const securityHeaders = [
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), browsing-topics=()",
  },
];

/** Server-only origin of the FastAPI service; the browser only ever calls same-origin /api paths. */
function apiOrigin(value = process.env.API_ORIGIN): string {
  const origin = new URL(value || "http://127.0.0.1:8000");
  if (!["http:", "https:"].includes(origin.protocol)) throw new Error("API_ORIGIN must be http(s)");
  return origin.origin;
}

const config: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin()}/api/:path*` }];
  },
};
export default config;
