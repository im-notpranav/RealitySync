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
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let accessTokenGetter: () => string | null = () => null;

/** The auth layer (T-008) registers how to read the in-memory access token. */
export function setAccessTokenGetter(getter: () => string | null): void {
  accessTokenGetter = getter;
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Not JSON (proxy error page, network layer); fall through to a generic error.
  }
  if (isErrorBody(body)) {
    const { code, message, details, request_id } = body.error;
    return new ApiError(response.status, code, message, details ?? [], request_id);
  }
  return new ApiError(response.status, "INTERNAL_ERROR", `Request failed with status ${response.status}`);
}

export interface ApiRequestInit extends Omit<RequestInit, "body"> {
  json?: unknown;
}

/** Fetch a REST endpoint under `/api/v1` (04). `path` starts with `/`, e.g. `/findings?status=open`. */
export async function apiFetch<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json");
  if (json !== undefined) requestHeaders.set("Content-Type", "application/json");

  const token = accessTokenGetter();
  if (token) requestHeaders.set("Authorization", `Bearer ${token}`);

  const isAuthPath = path.startsWith("/auth/");
  if (path.startsWith("/auth/refresh")) requestHeaders.set("X-Requested-With", "fetch");

  const response = await fetch(`${env.apiBaseUrl}/api/v1${path}`, {
    ...rest,
    headers: requestHeaders,
    body: json === undefined ? undefined : JSON.stringify(json),
    // Refresh cookie is scoped to /api/v1/auth (02 §5); other calls use bearer tokens only.
    credentials: isAuthPath ? "include" : "same-origin",
  });

  if (!response.ok) throw await parseApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
