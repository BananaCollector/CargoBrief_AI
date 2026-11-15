export const apiBaseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const responseText = await response.text();
    let message = responseText || `Request failed (${response.status})`;
    if (responseText) {
      try {
        const payload = JSON.parse(responseText) as { error?: { message?: string } };
        message = payload.error?.message ?? message;
      } catch {
        message = responseText;
      }
    }
    throw new ApiError(message, response.status);
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (response.status === 204 || !contentType.includes('application/json')) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}
