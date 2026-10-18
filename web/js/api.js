const API = '/api';
let token = null;

export function clearToken() {
  token = null;
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  let response;
  try {
    response = await fetch(API + path, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    throw new Error(
      error.name === 'AbortError'
        ? 'The request timed out.'
        : 'The server is unavailable.'
    );
  } finally {
    clearTimeout(timeout);
  }

  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    clearToken();
    throw new Error('Your session expired. Please sign in again.');
  }
  if (!response.ok) {
    throw new Error(data.detail?.message || data.detail || 'Request failed');
  }
  return data;
}

export async function download(path) {
  const headers = new Headers();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(API + path, { headers });
  if (!response.ok) throw new Error('Download failed');
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'talentiq-ranking.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function login(username, password) {
  const data = await request('/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  token = data.token;
  return data;
}

export const logout = () => request('/logout', { method: 'POST' }).finally(clearToken);
