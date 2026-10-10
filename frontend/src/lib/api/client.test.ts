import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch, parseApiError } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("parseApiError", () => {
  it("reads the 04 §1.3 envelope", async () => {
    const error = await parseApiError(
      jsonResponse(409, {
        error: {
          code: "CONFLICT",
          message: "Illegal transition",
          details: [{ message: "allowed: resolved" }],
          request_id: "req-1",
        },
      }),
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "CONFLICT", requestId: "req-1" });
    expect(error.details).toHaveLength(1);
  });

  it("falls back to a generic error for non-JSON bodies", async () => {
    const error = await parseApiError(new Response("<html>bad gateway</html>", { status: 502 }));
    expect(error).toMatchObject({ status: 502, code: "INTERNAL_ERROR" });
  });
});

describe("apiFetch", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends cookies only on auth paths and adds the refresh header", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/auth/refresh", { method: "POST" });
    await apiFetch("/findings");

    const [refreshCall, findingsCall] = fetchMock.mock.calls as unknown as [
      [string, RequestInit],
      [string, RequestInit],
    ];
    expect(refreshCall[0]).toBe("/api/v1/auth/refresh");
    expect(refreshCall[1].credentials).toBe("include");
    expect(new Headers(refreshCall[1].headers).get("X-Requested-With")).toBe("fetch");
    expect(findingsCall[1].credentials).toBe("same-origin");
  });

  it("returns undefined for 204", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 204 })),
    );
    await expect(apiFetch("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });
});
