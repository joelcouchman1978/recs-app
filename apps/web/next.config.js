/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const dest = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
    return [
      // Proxy all backend calls through /api/* to FastAPI root
      { source: '/api/:path*', destination: `${dest}/:path*` },
    ];
  },
};
module.exports = nextConfig;

