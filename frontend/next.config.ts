import type { NextConfig } from "next";

const backendUrl =
  process.env.BACKEND_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

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
    ];
  },
};

export default nextConfig;