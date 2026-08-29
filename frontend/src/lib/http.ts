import { CONFIG } from '../config';
import { CapacityConflictResponse } from '../types/api';

export interface ValidationErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export class ApiError extends Error {
  public status: number;
  public url: string;
  public method: string;
  public rawDetail: string | ValidationErrorDetail[] | Record<string, unknown> | null;
  public isCapacityConflict: boolean;
  public capacityConflictData?: CapacityConflictResponse;

  constructor(
    status: number,
    url: string,
    method: string,
    rawDetail: string | ValidationErrorDetail[] | Record<string, unknown> | null,
    conflictData?: CapacityConflictResponse
  ) {
    super(ApiError.extractMessage(rawDetail, status));
    this.name = 'ApiError';
    this.status = status;
    this.url = url;
    this.method = method;
    this.rawDetail = rawDetail;
    this.isCapacityConflict = status === 409 && !!conflictData?.candidate_actions;
    this.capacityConflictData = conflictData;
  }

  private static extractMessage(
    rawDetail: string | ValidationErrorDetail[] | Record<string, unknown> | null,
    status: number
  ): string {
    if (typeof rawDetail === 'string') {
      // Clean up backend 404 formatting (e.g., "'No case abc'" -> "No case abc")
      return rawDetail.replace(/^['"]|['"]$/g, '');
    }
    if (Array.isArray(rawDetail)) {
      // 422 Pydantic validation error array
      return rawDetail
        .map((item) => {
          const field = item.loc ? item.loc.filter((l) => l !== 'body').join('.') : '';
          return field ? `${field}: ${item.msg}` : item.msg;
        })
        .join('; ');
    }
    if (rawDetail && typeof rawDetail === 'object' && 'detail' in rawDetail && typeof rawDetail.detail === 'string') {
      return rawDetail.detail.replace(/^['"]|['"]$/g, '');
    }
    return `Request failed with HTTP ${status}`;
  }

  public displayMessage(): string {
    return this.message;
  }

  public getValidationErrors(): Record<string, string> {
    const errors: Record<string, string> = {};
    if (Array.isArray(this.rawDetail)) {
      for (const item of this.rawDetail) {
        const field = item.loc ? item.loc[item.loc.length - 1] : 'root';
        if (field) {
          errors[String(field)] = item.msg;
        }
      }
    }
    return errors;
  }
}

export interface RequestOptions extends RequestInit {
  auth?: boolean;
  params?: Record<string, string | number | boolean | undefined | null>;
  responseType?: 'json' | 'text';
}

function getStoredToken(): string | null {
  try {
    const raw = localStorage.getItem(CONFIG.AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed.token || parsed.access_token || null;
  } catch {
    return null;
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { auth = false, params, responseType = 'json', headers = {}, ...rest } = options;

  let url = `${CONFIG.API_BASE_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    }
    const query = searchParams.toString();
    if (query) {
      url += (url.includes('?') ? '&' : '?') + query;
    }
  }

  const reqHeaders: Record<string, string> = {
    ...(responseType === 'json' ? { Accept: 'application/json' } : { Accept: 'text/plain, */*' }),
    ...(headers as Record<string, string>),
  };

  if (auth) {
    const token = getStoredToken();
    if (token) {
      reqHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  if (rest.body && typeof rest.body === 'string' && !reqHeaders['Content-Type']) {
    reqHeaders['Content-Type'] = 'application/json';
  }

  const method = rest.method || 'GET';

  let res: Response;
  try {
    res = await fetch(url, {
      ...rest,
      method,
      headers: reqHeaders,
    });
  } catch (err: unknown) {
    throw new ApiError(
      0,
      url,
      method,
      err instanceof Error ? `Network error: ${err.message}` : 'Network error'
    );
  }

  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('patienttriage:session-expired'));
  }

  if (!res.ok) {
    let rawDetail: string | ValidationErrorDetail[] | Record<string, unknown> | null = null;
    let conflictData: CapacityConflictResponse | undefined;

    try {
      const errorJson = await res.json();
      rawDetail = errorJson.detail !== undefined ? errorJson.detail : errorJson;
      if (res.status === 409 && errorJson.candidate_actions) {
        conflictData = errorJson as CapacityConflictResponse;
      }
    } catch {
      try {
        rawDetail = await res.text();
      } catch {
        rawDetail = res.statusText;
      }
    }

    throw new ApiError(res.status, url, method, rawDetail, conflictData);
  }

  if (responseType === 'text') {
    const text = await res.text();
    return text as unknown as T;
  }

  if (res.status === 204) {
    return null as unknown as T;
  }

  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return (await res.json()) as T;
  }

  // Fallback for non-json 200 bodies
  const text = await res.text();
  if (!text) return null as unknown as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

export const http = {
  get: <T>(endpoint: string, options?: Omit<RequestOptions, 'method'>) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  put: <T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: Omit<RequestOptions, 'method'>) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};
