import { env } from "../env";

/** Error envelope from 04 §1.3. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: { field?: string; message: string }[];
    request_id?: string;
  };
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: { field?: string; message: string }[] = [],
    readonly requestId?: string,
    /** Seconds from the `Retry-After` header of a `429` (04 §15). */
    readonly retryAfter?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface AuthHandlers {
  getAccessToken: () => string | null;
  /** Get a fresh access token (single in-flight refresh); null when the session is gone. */
  refreshAccessToken: () => Promise<string | null>;
}

let authHandlers: AuthHandlers = {
  getAccessToken: () => null,
  refreshAccessToken: () => Promise.resolve(null),
};

/** The auth layer (`lib/api/auth.ts`) registers how to read and renew the in-memory access token. */
export function setAuthHandlers(handlers: AuthHandlers): void {
  authHandlers = handlers;
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

function retryAfterSeconds(response: Response): number | undefined {
  const raw = response.headers.get("Retry-After");
  const seconds = raw === null ? Number.NaN : Number(raw);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : undefined;
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Not JSON (proxy error page, network layer); fall through to a generic error.
  }
  const retryAfter = retryAfterSeconds(response);
  if (isErrorBody(body)) {
    const { code, message, details, request_id } = body.error;
    return new ApiError(response.status, code, message, details ?? [], request_id, retryAfter);
  }
  return new ApiError(
    response.status,
    "INTERNAL_ERROR",
    `Request failed with status ${response.status}`,
    [],
    undefined,
    retryAfter,
  );
}

export interface ApiRequestInit extends Omit<RequestInit, "body"> {
  json?: unknown;
}

function send(path: string, init: ApiRequestInit, token: string | null): Promise<Response> {
  const { json, headers, ...rest } = init;
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json");
  if (json !== undefined) requestHeaders.set("Content-Type", "application/json");
  if (token) requestHeaders.set("Authorization", `Bearer ${token}`);
  if (path.startsWith("/auth/refresh")) requestHeaders.set("X-Requested-With", "fetch");

  return fetch(`${env.apiBaseUrl}/api/v1${path}`, {
    ...rest,
    headers: requestHeaders,
    body: json === undefined ? undefined : JSON.stringify(json),
    // Refresh cookie is scoped to /api/v1/auth (02 §5); other calls use bearer tokens only.
    credentials: path.startsWith("/auth/") ? "include" : "same-origin",
  });
}

/**
 * Fetch a REST endpoint under `/api/v1` (04). `path` starts with `/`, e.g. `/findings?status=open`.
 *
 * A `401` outside `/auth/*` triggers one silent refresh and one retry; concurrent requests share the
 * same refresh (02 §3.1).
 */
export async function apiFetch<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  let response = await send(path, init, authHandlers.getAccessToken());

  if (response.status === 401 && !path.startsWith("/auth/")) {
    const token = await authHandlers.refreshAccessToken();
    if (token) response = await send(path, init, token);
  }

  if (!response.ok) throw await parseApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
