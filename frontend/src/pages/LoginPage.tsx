import { motion } from "motion/react";
import { useId, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LogoMark } from "../app/shell/Logo";
import { Scene } from "../app/shell/Scene";
import { Button, Field, Input } from "../components/ui";
import { env } from "../lib/env";
import { EASE_OUT } from "../lib/motion";
import { useSession } from "../store/session";

/**
 * Sign-in (design). T-008 connects the form to POST /auth/login; until then development builds sign in
 * as the local demo admin.
 */
export function Component() {
  const navigate = useNavigate();
  const setSession = useSession((state) => state.setSession);
  const ids = { email: useId(), password: useId() };
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="relative isolate grid min-h-dvh place-items-center p-4">
      <Scene />
      <motion.div
        initial={{ opacity: 0, transform: "translateY(8px)" }}
        animate={{ opacity: 1, transform: "translateY(0px)" }}
        transition={{ duration: 0.3, ease: EASE_OUT }}
        className="glass-panel w-full max-w-[420px] rounded-panel p-2 shadow-panel"
      >
        <div className="rounded-[22px] bg-paper p-8 shadow-card">
          <div className="flex items-center gap-3">
            <LogoMark className="size-10" />
            <span className="text-[19px] font-semibold tracking-[-0.02em] text-ink-950">RealitySync</span>
          </div>
          <h1 className="mt-8 text-h2 text-ink-950">Sign in</h1>
          <p className="mt-1 text-small text-ink-500">
            Organizational Reality Intelligence for your CRM, Billing and Support data.
          </p>
          <form
            className="mt-6 flex flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (!env.isDevelopment) {
                setError("Sign-in is not connected yet.");
                return;
              }
              setSession({ id: "dev-admin", fullName: "Demo Admin", role: "admin" }, "");
              navigate("/");
            }}
          >
            <Field label="Email" htmlFor={ids.email}>
              <Input
                id={ids.email}
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                required={!env.isDevelopment}
              />
            </Field>
            <Field label="Password" htmlFor={ids.password}>
              <Input
                id={ids.password}
                type="password"
                autoComplete="current-password"
                required={!env.isDevelopment}
              />
            </Field>
            {error ? (
              <p role="alert" className="text-small text-rose-fg">
                {error}
              </p>
            ) : null}
            <Button type="submit" variant="primary" className="mt-2 w-full">
              {env.isDevelopment ? "Continue as demo admin" : "Sign in"}
            </Button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
