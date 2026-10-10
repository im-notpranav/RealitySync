import { render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { useSession, type SessionUser } from "../store/session";
import { Providers } from "./providers";
import { routerFuture, routes } from "./routes";

const initialUser = useSession.getState().user;

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path], future: routerFuture });
  render(
    <Providers>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>,
  );
}

function signInAs(role: SessionUser["role"]) {
  useSession.setState({ user: { id: "u1", fullName: "Riya Sharma", role } });
}

afterEach(() => useSession.setState({ user: initialUser }));

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

  it("tells viewers when a page needs another role", async () => {
    signInAs("viewer");
    renderAt("/rules");
    expect(await screen.findByText("You don't have access to this page")).toBeInTheDocument();
  });

  it("renders a not-found page for unknown paths", async () => {
    signInAs("viewer");
    renderAt("/does-not-exist");
    expect(await screen.findByRole("heading", { level: 1, name: "Page not found" })).toBeInTheDocument();
  });
});
