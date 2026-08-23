import type { NextConfig } from "next";

const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  trailingSlash: false,
  // Same-origin proxy so browser EventSource/fetch can send HttpOnly jwt cookie
  // (cookie is on Next origin; backend accepts Cookie: jwt=…).
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backend.replace(/\/$/, "")}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
