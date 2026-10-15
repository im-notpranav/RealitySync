import { motion } from "motion/react";
import { useId, useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { LogoMark } from "../../app/shell/Logo";
import { Scene } from "../../app/shell/Scene";
import { Button, Field, Input } from "../../components/ui";
import { signIn } from "../../lib/api/auth";
import { env } from "../../lib/env";
import { EASE_OUT } from "../../lib/motion";
import { useSession, type SessionUser } from "../../store/session";
import { signInErrorMessage } from "./messages";
import { safeNext } from "./redirect";
import { useSessionBootstrap } from "./useSessionBootstrap";

const DEMO_USER: SessionUser = {
  id: "demo-admin",
  email: "demo@realitysync.test",
  fullName: "Demo Admin",
  role: "admin",
};

/** Sign-in (04 §2 `POST /auth/login`). The access token stays in memory; the refresh cookie is httpOnly. */
export function Component() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const status = useSession((state) => state.status);
  const startDemo = useSession((state) => state.startDemo);
  const ids = { email: useId(), password: useId() };
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const next = safeNext(params.get("next"));
  useSessionBootstrap();

  if (status === "authenticated") return <Navigate to={next} replace />;

  function exploreDemo() {
    startDemo(DEMO_USER);
    navigate(next, { replace: true });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
      navigate(next, { replace: true });
    } catch (caught) {
      setError(signInErrorMessage(caught));
      setPassword("");
    } finally {
      setPending(false);
    }
  }

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
          {env.demoOnly ? (
            <>
              <h1 className="mt-8 text-h2 text-ink-950">Public demo</h1>
              <p className="mt-1 text-small text-ink-500">
                Organizational Reality Intelligence for your CRM, Billing and Support data. Every screen runs
                on synthetic data; nothing you change is saved.
              </p>
              <Button variant="primary" className="mt-6 w-full" onClick={exploreDemo}>
                Explore with demo data
              </Button>
              <p className="mt-2 text-center text-caption text-ink-500">
                You browse as {DEMO_USER.fullName}, with access to every screen.
              </p>
            </>
          ) : (
            <>
              <h1 className="mt-8 text-h2 text-ink-950">Sign in</h1>
              <p className="mt-1 text-small text-ink-500">
                Organizational Reality Intelligence for your CRM, Billing and Support data.
              </p>
              <form className="mt-6 flex flex-col gap-4" onSubmit={onSubmit}>
                <Field label="Email" htmlFor={ids.email}>
                  <Input
                    id={ids.email}
                    type="email"
                    autoComplete="email"
                    placeholder="you@company.com"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </Field>
                <Field label="Password" htmlFor={ids.password}>
                  <Input
                    id={ids.password}
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </Field>
                {error ? (
                  <p role="alert" className="text-small text-rose-fg">
                    {error}
                  </p>
                ) : null}
                <Button type="submit" variant="primary" className="mt-2 w-full" disabled={pending}>
                  {pending ? "Signing in…" : "Sign in"}
                </Button>
              </form>
              {env.demoData ? (
                <div className="mt-6 border-t border-ink-100 pt-5">
                  <Button variant="secondary" surface="paper" className="w-full" onClick={exploreDemo}>
                    Explore with demo data
                  </Button>
                  <p className="mt-2 text-center text-caption text-ink-500">
                    Development only. Synthetic data, no backend needed.
                  </p>
                </div>
              ) : null}
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
