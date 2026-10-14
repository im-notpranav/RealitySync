import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSession } from "../../store/session";
import { refreshAccessToken, signIn, signOut } from "./auth";
import { apiFetch } from "./client";

const USER = { id: "u1", email: "riya.sharma@example.com", full_name: "Riya Sharma", role: "analyst" };

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function tokens(access: string): Response {
  return json(200, { access_token: access, token_type: "bearer", expires_in: 900, user: USER });
}

const unauthenticated = () => json(401, { error: { code: "UNAUTHENTICATED", message: "Expired" } });

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>;

function mockFetch(handler: Handler) {
  const fetchMock = vi.fn(async (url: string, init: RequestInit) => handler(url, init));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function calls(fetchMock: ReturnType<typeof mockFetch>, path: string) {
  return fetchMock.mock.calls.filter(([url]) => url === `/api/v1${path}`);
}

function authorization(init: RequestInit): string | null {
  return new Headers(init.headers).get("Authorization");
}

beforeEach(() => useSession.setState({ status: "unknown", user: null, accessToken: null, isDemo: false }));
afterEach(() => vi.unstubAllGlobals());

describe("signIn", () => {
  it("keeps the access token in memory and maps the user", async () => {
    const fetchMock = mockFetch(() => tokens("t1"));

    await signIn("riya.sharma@example.com", "Correct-horse-42");

    expect(useSession.getState()).toMatchObject({
      status: "authenticated",
      accessToken: "t1",
      user: { id: "u1", email: "riya.sharma@example.com", fullName: "Riya Sharma", role: "analyst" },
    });
    const [, init] = calls(fetchMock, "/auth/login")[0]!;
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body as string)).toEqual({
      email: "riya.sharma@example.com",
      password: "Correct-horse-42",
    });
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});

describe("silent refresh", () => {
  it("retries a 401 once with the refreshed token", async () => {
    useSession.getState().setSession({ id: "u1", email: "", fullName: "Riya", role: "analyst" }, "old");
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith("/auth/refresh")) return tokens("new");
      return authorization(init) === "Bearer new" ? json(200, { items: [] }) : unauthenticated();
    });

    await expect(apiFetch("/findings")).resolves.toEqual({ items: [] });

    expect(calls(fetchMock, "/auth/refresh")).toHaveLength(1);
    const findings = calls(fetchMock, "/findings");
    expect(findings.map(([, init]) => authorization(init))).toEqual(["Bearer old", "Bearer new"]);
  });

  it("shares one refresh between concurrent 401s", async () => {
    useSession.getState().setSession({ id: "u1", email: "", fullName: "Riya", role: "analyst" }, "old");
    let releaseRefresh: (response: Response) => void = () => undefined;
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith("/auth/refresh"))
        return new Promise<Response>((resolve) => (releaseRefresh = resolve));
      return authorization(init) === "Bearer new" ? json(200, { ok: url }) : unauthenticated();
    });

    const requests = Promise.all([apiFetch("/findings"), apiFetch("/alerts"), apiFetch("/entities")]);
    await vi.waitFor(() => expect(calls(fetchMock, "/auth/refresh")).toHaveLength(1));
    releaseRefresh(tokens("new"));

    await expect(requests).resolves.toHaveLength(3);
    expect(calls(fetchMock, "/auth/refresh")).toHaveLength(1);
  });

  it("signs out when the refresh is rejected, and surfaces the original 401", async () => {
    useSession.getState().setSession({ id: "u1", email: "", fullName: "Riya", role: "analyst" }, "old");
    const fetchMock = mockFetch(() => unauthenticated());

    await expect(apiFetch("/findings")).rejects.toMatchObject({ status: 401, code: "UNAUTHENTICATED" });

    expect(useSession.getState()).toMatchObject({ status: "anonymous", accessToken: null, user: null });
    expect(calls(fetchMock, "/findings")).toHaveLength(1);
  });

  it("keeps a live session when the network drops during a refresh", async () => {
    useSession.getState().setSession({ id: "u1", email: "", fullName: "Riya", role: "analyst" }, "old");
    mockFetch(() => Promise.reject(new TypeError("Failed to fetch")));

    await expect(refreshAccessToken()).resolves.toBeNull();

    expect(useSession.getState().status).toBe("authenticated");
  });

  it("treats an unreachable server on first load as signed out", async () => {
    mockFetch(() => Promise.reject(new TypeError("Failed to fetch")));

    await expect(refreshAccessToken()).resolves.toBeNull();

    expect(useSession.getState().status).toBe("anonymous");
  });

  it("sends the CSRF header and cookie on refresh", async () => {
    const fetchMock = mockFetch(() => tokens("t1"));

    await refreshAccessToken();

    const [, init] = calls(fetchMock, "/auth/refresh")[0]!;
    expect(new Headers(init.headers).get("X-Requested-With")).toBe("fetch");
    expect(init.credentials).toBe("include");
  });

  it("never refreshes for a failing auth call", async () => {
    const fetchMock = mockFetch(() => unauthenticated());

    await expect(signIn("riya.sharma@example.com", "wrong")).rejects.toMatchObject({ status: 401 });

    expect(calls(fetchMock, "/auth/refresh")).toHaveLength(0);
  });
});

describe("signOut", () => {
  it("revokes the session on the server and forgets it locally", async () => {
    useSession.getState().setSession({ id: "u1", email: "", fullName: "Riya", role: "analyst" }, "t1");
    const fetchMock = mockFetch(() => new Response(null, { status: 204 }));

    await signOut();

    const [, init] = calls(fetchMock, "/auth/logout")[0]!;
    expect(authorization(init)).toBe("Bearer t1");
    expect(init.credentials).toBe("include");
    expect(useSession.getState()).toMatchObject({ status: "anonymous", accessToken: null });
  });

  it("renews an expired access token so the server can still revoke the family", async () => {
    useSession.getState().setSession({ id: "u1", email: "", fullName: "Riya", role: "analyst" }, "expired");
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith("/auth/refresh")) return tokens("fresh");
      return authorization(init) === "Bearer fresh" ? new Response(null, { status: 204 }) : unauthenticated();
    });

    await signOut();

    expect(calls(fetchMock, "/auth/logout").map(([, init]) => authorization(init))).toEqual([
      "Bearer expired",
      "Bearer fresh",
    ]);
    expect(useSession.getState().status).toBe("anonymous");
  });

  it("clears the local session even when the server is unreachable", async () => {
    useSession.getState().setSession({ id: "u1", email: "", fullName: "Riya", role: "analyst" }, "t1");
    mockFetch(() => Promise.reject(new TypeError("Failed to fetch")));

    await signOut();

    expect(useSession.getState().status).toBe("anonymous");
  });

  it("does not call the server for a demo session", async () => {
    useSession.getState().startDemo({ id: "demo", email: "", fullName: "Demo", role: "admin" });
    const fetchMock = mockFetch(() => new Response(null, { status: 204 }));

    await signOut();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(useSession.getState().status).toBe("anonymous");
  });
});
