import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Providers } from "../../app/providers";
import { routerFuture, routes } from "../../app/routes";
import { ApiError } from "../../lib/api/client";
import { useSession } from "../../store/session";
import { signInErrorMessage } from "./messages";
import { loginPath, safeNext } from "./redirect";

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function renderLogin(path = "/login") {
  const router = createMemoryRouter(routes, { initialEntries: [path], future: routerFuture });
  render(
    <Providers>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>,
  );
  return router;
}

async function submit(email: string, password: string) {
  const user = userEvent.setup({ delay: null });
  await user.type(await screen.findByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

beforeEach(() => useSession.getState().clear());
afterEach(() => vi.unstubAllGlobals());

describe("safeNext", () => {
  it.each([
    [null, "/"],
    ["", "/"],
    ["/findings?status=open", "/findings?status=open"],
    ["/entities/e1?at=2026-07-02T00:00:00Z", "/entities/e1?at=2026-07-02T00:00:00Z"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
    ["/login", "/"],
    ["/login?next=/rules", "/"],
  ])("%s → %s", (raw, expected) => {
    expect(safeNext(raw)).toBe(expected);
  });

  it("round-trips through loginPath", () => {
    expect(loginPath("/")).toBe("/login");
    const path = loginPath("/findings?status=open&q=a b");
    expect(safeNext(new URLSearchParams(path.split("?")[1]).get("next"))).toBe("/findings?status=open&q=a b");
  });
});

describe("signInErrorMessage", () => {
  it.each([
    [new ApiError(401, "INVALID_CREDENTIALS", "x"), "Email or password is incorrect."],
    [
      new ApiError(429, "RATE_LIMITED", "x", [], undefined, 42),
      "Too many attempts. Try again in 42 seconds.",
    ],
    [new ApiError(429, "RATE_LIMITED", "x", [], undefined, 1), "Too many attempts. Try again in 1 second."],
    [new ApiError(422, "VALIDATION_ERROR", "x"), "Enter a valid email address and your password."],
    [new ApiError(500, "INTERNAL_ERROR", "x"), "Something went wrong. Try again."],
    [new TypeError("Failed to fetch"), "Can't reach RealitySync. Check your connection and try again."],
  ])("%s", (error, message) => {
    expect(signInErrorMessage(error)).toBe(message);
  });
});

describe("login page", () => {
  it("signs in and returns to the page the user wanted", async () => {
    const fetchMock = vi.fn(async () =>
      json(200, {
        access_token: "t1",
        token_type: "bearer",
        expires_in: 900,
        user: { id: "u1", email: "riya.sharma@example.com", full_name: "Riya Sharma", role: "viewer" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const router = renderLogin(`/login?next=${encodeURIComponent("/alerts")}`);

    await submit("riya.sharma@example.com", "Correct-horse-42");

    expect(await screen.findByRole("heading", { level: 1, name: "Alerts" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/alerts");
    expect(useSession.getState()).toMatchObject({ status: "authenticated", accessToken: "t1" });
  });

  it("explains a wrong password and clears the password field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        json(401, { error: { code: "INVALID_CREDENTIALS", message: "Invalid email or password" } }),
      ),
    );
    renderLogin();

    await submit("riya.sharma@example.com", "Wrong-password-1");

    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(useSession.getState().status).toBe("anonymous");
  });

  it("shows how long to wait when rate limited", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        json(429, { error: { code: "RATE_LIMITED", message: "Too many requests" } }, { "Retry-After": "55" }),
      ),
    );
    renderLogin();

    await submit("riya.sharma@example.com", "Correct-horse-42");

    expect(await screen.findByRole("alert")).toHaveTextContent("Too many attempts. Try again in 55 seconds.");
  });

  it("offers demo data in development and skips the backend", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();

    await userEvent
      .setup({ delay: null })
      .click(await screen.findByRole("button", { name: "Explore with demo data" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
    expect(useSession.getState()).toMatchObject({ status: "authenticated", isDemo: true, accessToken: null });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends a signed-in visitor straight on", async () => {
    useSession
      .getState()
      .setSession(
        { id: "u1", email: "riya.sharma@example.com", fullName: "Riya Sharma", role: "viewer" },
        "t",
      );

    const router = renderLogin("/login");

    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("account menu", () => {
  it("lists profile, users for admins, and signs out", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    useSession
      .getState()
      .setSession({ id: "u1", email: "ana.lopez@example.com", fullName: "Ana Lopez", role: "admin" }, "t");
    const router = renderLogin("/");
    const user = userEvent.setup({ delay: null });

    await user.click(await screen.findByRole("button", { name: "Account menu" }));
    expect(screen.getByText("ana.lopez@example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Profile" })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: "Users" })).toHaveAttribute("href", "/settings?tab=users");

    await user.click(
      within(screen.getByRole("group", { name: "Account" })).getByRole("button", { name: "Sign out" }),
    );

    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
    expect(useSession.getState().status).toBe("anonymous");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("hides the users link from non-admins and closes on Escape", async () => {
    useSession
      .getState()
      .setSession(
        { id: "u1", email: "riya.sharma@example.com", fullName: "Riya Sharma", role: "analyst" },
        "t",
      );
    renderLogin("/");
    const user = userEvent.setup({ delay: null });

    const trigger = await screen.findByRole("button", { name: "Account menu" });
    await user.click(trigger);
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveFocus();
  });
});
