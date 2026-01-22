import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // [추가] 윈도우 Docker 환경에서 Hot Reload가 안 될 때를 위한 강제 설정
  webpack: (config) => {
    config.watchOptions = {
      poll: 300,      // 300ms마다 변경 사항 확인
      aggregateTimeout: 300,
    }
    return config
  },

  async rewrites() {
    return [
      {
        source: '/api/chat',
        destination: 'http://backend:8000/chat',
      },
      {
        source: '/api/users/:path*',
        destination: 'http://backend:8000/users/:path*',
      },
    ];
  },
};

export default nextConfig;