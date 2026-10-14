import { LogoMark } from "../../app/shell/Logo";
import { Scene } from "../../app/shell/Scene";

/** Shown for the moment the first silent refresh takes, so no page flashes before the redirect. */
export function SessionSplash() {
  return (
    <div className="relative isolate grid min-h-dvh place-items-center" role="status" aria-live="polite">
      <Scene />
      <div className="flex flex-col items-center gap-3">
        <LogoMark className="size-10" />
        <p className="text-small text-ink-500">Checking your session…</p>
      </div>
    </div>
  );
}
