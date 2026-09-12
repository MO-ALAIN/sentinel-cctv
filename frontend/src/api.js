export const API = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
export const apiUrl = (path) => `${API}${path}`;
export const normalizePlate = (value) => value.toUpperCase().replace(/[^A-Z0-9]/g, '');
export async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeout || 20000);
  try {
    const response = await fetch(apiUrl(path), {
      credentials: 'include', ...options, signal: options.signal || controller.signal,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    });
    if (!response.ok) {
      let message;
      try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail); }
      catch { message = `Request failed (${response.status})`; }
      throw new Error(message);
    }
    return response.json();
  } finally { clearTimeout(timer); }
}
export const localTime = (value) => value ? new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'medium' }) : '—';
export async function downloadReport(path, filename) {
  const response = await fetch(apiUrl(path), { credentials: 'include' });
  if (!response.ok) throw new Error(`Export failed (${response.status})`);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
