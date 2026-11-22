async function request(url: string, method = "GET", body?: unknown): Promise<Response> {
  const options: RequestInit = { method };
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) {
    options.body = JSON.stringify(body);
    options.headers = { "Content-Type": "application/json" };
  }
  const response = await fetch("/api" + url, options);
  if (!response.ok) {
    const data = await response.json().catch(()=>null);
    const message = typeof data?.detail === "string" ? data.detail : JSON.stringify(data?.detail);
    throw new Error(message || `Request failed (HTTP ${response.status})`);
  }
  return response;
}
export async function api<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  return (await request(url,method,body)).json();
}

export async function apiBlob(url: string, method = "GET", body?: unknown) {
  return (await request(url,method,body)).blob();
}

export const errorMessage = (e: unknown) => e instanceof Error ? e.message : String(e);
