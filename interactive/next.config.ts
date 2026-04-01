import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  output: "export",
  basePath: isProd ? "/agent-reasoning/interactive" : "",
  assetPrefix: isProd ? "/agent-reasoning/interactive/" : "",
  images: { unoptimized: true },
};

export default nextConfig;
