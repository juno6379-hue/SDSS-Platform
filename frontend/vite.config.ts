import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

// 선택한 개발 서버만 동일 출처로 프록시하며 API의 CORS·인증 설정은 바꾸지 않는다.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, fileURLToPath(new URL('.', import.meta.url)), 'VITE_');
  const target = env.VITE_API_PROXY_TARGET;
  const paths = ['/api', '/v1', '/healthz', '/readyz', '/docs', '/openapi.json'];
  return {
    plugins: [react()],
    ...(target ? { server: { proxy: Object.fromEntries(paths.map(path => [path, { target, changeOrigin: true }])) } } : {}),
  };
});
