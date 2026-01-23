import type { NextConfig } from "next";

const backendUrl =
  process.env.BACKEND_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

const rawLayeringApiUrl =
  process.env.LAYERING_API_URL ??
  process.env.NEXT_PUBLIC_LAYERING_API_URL ??
  "http://localhost:8002";

const normalizedLayeringApiUrl = rawLayeringApiUrl.replace(/\/+$/, "");
const layeringApiUrl = normalizedLayeringApiUrl.endsWith("/layering")
  ? normalizedLayeringApiUrl.slice(0, -"/layering".length)
  : normalizedLayeringApiUrl;

const nextConfig: NextConfig = {
  // [추가] 윈도우 Docker 환경에서 Hot Reload가 안 될 때를 위한 강제 설정
  webpack: (config) => {
    config.watchOptions = {
      poll: 300,      // 300ms마다 변경 사항 확인
      aggregateTimeout: 300,
    }
    return config
  },
  turbopack: {},

  async rewrites() {
    return [
      {
        source: '/api/chat',
        destination: `${backendUrl}/chat`,
      },
      {
        source: '/api/users/:path*',
        destination: `${backendUrl}/users/:path*`,
      },
      {
        source: '/api/layering/:path*',
        destination: `${layeringApiUrl}/layering/:path*`,
      },
    ];
  },
};

export default nextConfig;
