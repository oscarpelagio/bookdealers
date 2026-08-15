const BASE_URL = process.env.EXPO_PUBLIC_API_URL;

if (!BASE_URL) {
  throw new Error('EXPO_PUBLIC_API_URL is not defined');
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type UnauthorizedHandler = () => Promise<boolean>;

let accessToken: string | null = null;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setAuthAccessToken(token: string | null) {
  accessToken = token;
}

export function getAuthAccessToken(): string | null {
  return accessToken;
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler;
}

async function request<T>(path: string, options?: RequestInit, retried = false): Promise<T> {
  const headers = new Headers(options?.headers);
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError('Network error', 0, 'NETWORK_ERROR');
  }

  if (response.status === 401 && unauthorizedHandler && !retried) {
    const retryable = await unauthorizedHandler();
    if (retryable) {
      return request<T>(path, options, true);
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));

    // Auth-style errors: { error: <code>, message }
    if (typeof body.error === 'string' && typeof body.message === 'string') {
      throw new ApiError(body.message, response.status, body.error);
    }

    let message = body.detail ?? `Request failed with status ${response.status}`;
    if (typeof message === 'string' && message.startsWith('[') && message.endsWith(']')) {
      const parsed = JSON.parse(message) as { msg: string }[];
      message = parsed[0]?.msg ?? message;
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function buildQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.append(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export const apiClient = {
  get: <T>(path: string, params?: Record<string, unknown>, options?: RequestInit) =>
    request<T>(`${path}${buildQuery(params ?? {})}`, options),
  post: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      ...options,
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      ...options,
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'DELETE', ...options }),
  BASE_URL,
};