export const API_BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000/api').replace(/\/$/, '');
function authHeaders(): Record<string, string> {
  const token = sessionStorage.getItem('geoai_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}
// 서버가 반환한 오류를 그대로 전달해 외부 데이터·학습 실패를 숨기지 않는다.
export async function api<T = unknown>(path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = body === undefined ? {} : { 'Content-Type': 'application/json' };
  // 공유 서버의 토큰은 탭 세션 동안만 sessionStorage에 보관하며 영구 저장하지 않는다.
  Object.assign(headers, authHeaders());
  const response = await fetch(`${API_BASE}${path}`, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const content = await response.text();
  if (response.ok && !response.headers.get('content-type')?.includes('json')) return content as T;
  let data: unknown;
  try { data = content ? JSON.parse(content) : null; } catch { throw new Error(`HTTP ${response.status}: ${content.slice(0, 300)}`); }
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${JSON.stringify(data)}`);
  return data as T;
}
// 인증 헤더를 유지한 다운로드다. 보고서와 산출물을 새 탭의 비인증 URL로 열지 않는다.
export async function downloadApi(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${(await response.text()).slice(0, 300)}`);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url; link.download = filename.split(/[\\/]/).pop() || 'artifact';
  document.body.appendChild(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// v0.2 Agent API는 기존 /api 하위가 아닌 같은 서버 origin의 /v1을 사용한다.
export async function agentApi<T = unknown>(path: string, body?: unknown, idempotencyKey?: string): Promise<T> {
  if (!path.startsWith('/v1/')) throw new Error('표준 Agent API 경로는 /v1/이어야 합니다.');
  const origin = new URL(API_BASE, window.location.href).origin;
  const headers: Record<string, string> = { ...authHeaders(), ...(body === undefined ? {} : {'Content-Type': 'application/json'}) };
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
  const response = await fetch(origin + path, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await response.text();
  let value: unknown;
  try { value = text ? JSON.parse(text) : null; } catch { throw new Error(`HTTP ${response.status}: ${text.slice(0,300)}`); }
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${JSON.stringify(value)}`);
  return value as T;
}
