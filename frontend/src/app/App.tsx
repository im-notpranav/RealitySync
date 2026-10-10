import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Providers } from "./providers";
import { routerFuture, routes } from "./routes";

const router = createBrowserRouter(routes, { future: routerFuture });

export function App() {
  return (
    <Providers>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>
  );
}
