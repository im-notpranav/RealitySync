import { render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSession, type SessionUser } from "../store/session";
import { Providers } from "./providers";
import { routerFuture, routes } from "./routes";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path], future: routerFuture });
  render(
    <Providers>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>,
  );
  return router;
}

function signInAs(role: SessionUser["role"]) {
  useSession
    .getState()
    .setSession({ id: "u1", email: "riya.sharma@example.com", fullName: "Riya Sharma", role }, "token");
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => useSession.setState({ status: "unknown", user: null, accessToken: null, isDemo: false }));
afterEach(() => vi.unstubAllGlobals());

describe("app shell", () => {
  it("renders the overview inside the shell", async () => {
    signInAs("admin");
    renderAt("/");
    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("search")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Skip to content" })).toBeInTheDocument();
  });

  it("shows admin navigation to admins only", async () => {
    signInAs("admin");
    renderAt("/");
    const [sidebar] = await screen.findAllByRole("navigation", { name: "Primary" });
    expect(within(sidebar!).getByRole("link", { name: "Rules" })).toBeInTheDocument();
    expect(within(sidebar!).getByRole("link", { name: "Link review" })).toBeInTheDocument();
  });

  it("hides analyst and admin navigation from viewers", async () => {
    signInAs("viewer");
    renderAt("/");
    const [sidebar] = await screen.findAllByRole("navigation", { name: "Primary" });
    expect(within(sidebar!).queryByRole("link", { name: "Rules" })).not.toBeInTheDocument();
    expect(within(sidebar!).queryByRole("link", { name: "Link review" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "New investigation" })).not.toBeInTheDocument();
  });

  it("renders a not-found page for unknown paths", async () => {
    signInAs("viewer");
    renderAt("/does-not-exist");
    expect(await screen.findByRole("heading", { level: 1, name: "Page not found" })).toBeInTheDocument();
  });
});

describe("route guards (02 §3.1)", () => {
  it.each([
    ["/review", "viewer"],
    ["/rules", "analyst"],
    ["/systems", "viewer"],
    ["/simulation", "analyst"],
    ["/simulation/run-1/evaluation", "analyst"],
  ] as const)("blocks %s for a %s", async (path, role) => {
    signInAs(role);
    renderAt(path);
    expect(await screen.findByText("You don't have access to this page")).toBeInTheDocument();
  });

  it.each([
    ["/review", "analyst", "Link review"],
    ["/rules", "admin", "Rules"],
  ] as const)("opens %s for a %s", async (path, role, heading) => {
    signInAs(role);
    renderAt(path);
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(screen.queryByText("You don't have access to this page")).not.toBeInTheDocument();
  });

  it("sends anonymous visitors to sign in and remembers where they were going", async () => {
    useSession.getState().clear();
    const router = renderAt("/findings?status=open");
    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
    expect(new URLSearchParams(router.state.location.search).get("next")).toBe("/findings?status=open");
  });

  it("restores the session from the refresh cookie on load", async () => {
    const fetchMock = vi.fn(async (_url: string) =>
      json(200, {
        access_token: "fresh",
        token_type: "bearer",
        expires_in: 900,
        user: { id: "u1", email: "riya.sharma@example.com", full_name: "Riya Sharma", role: "analyst" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderAt("/");

    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/auth/refresh");
    expect(useSession.getState()).toMatchObject({ status: "authenticated", accessToken: "fresh" });
  });

  it("shows sign-in when there is no session to restore", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json(401, { error: { code: "UNAUTHENTICATED", message: "Missing refresh token" } })),
    );

    const router = renderAt("/");

    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.search).toBe(""));
  });
});
