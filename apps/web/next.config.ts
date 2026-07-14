import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone: self-contained server bundle for the production Docker image
  // (deploy plan 2026-07-13); no effect on `next dev`.
  output: "standalone",
};

export default nextConfig;
