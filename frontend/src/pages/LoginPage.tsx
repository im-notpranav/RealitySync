import { useNavigate } from "react-router-dom";

import { LogoMark } from "../app/shell/Logo";
import { Scene } from "../app/shell/Scene";
import { Button, Card } from "../components/ui";
import { env } from "../lib/env";
import { useSession } from "../store/session";

/** Placeholder until T-008 builds the sign-in form. */
export function Component() {
  const navigate = useNavigate();
  const setSession = useSession((state) => state.setSession);

  return (
    <div className="relative isolate grid min-h-dvh place-items-center p-4">
      <Scene />
      <Card className="w-full max-w-sm p-8 shadow-raised">
        <LogoMark className="size-10" />
        <h1 className="mt-6 text-h2 text-ink-950">Sign in to RealitySync</h1>
        <p className="mt-2 text-small text-ink-500">The sign-in form arrives with task T-008.</p>
        {env.isDevelopment ? (
          <Button
            variant="primary"
            className="mt-8 w-full"
            onClick={() => {
              setSession({ id: "dev-admin", fullName: "Demo Admin", role: "admin" }, "");
              navigate("/");
            }}
          >
            Continue as demo admin
          </Button>
        ) : null}
      </Card>
    </div>
  );
}
