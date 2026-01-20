import type { NextConfig } from "next"; // 이 줄이 꼭 있어야 합니다

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/chat',
        destination: 'http://backend:8000/chat',
      },
    ];
  },
};

export default nextConfig;