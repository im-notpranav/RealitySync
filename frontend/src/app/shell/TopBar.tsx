import { Bell, Search, Settings } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Avatar, IconLink } from "../../components/ui";
import { env } from "../../lib/env";
import { useSession } from "../../store/session";

const isApplePlatform = typeof navigator !== "undefined" && /Mac|iPhone|iPad/i.test(navigator.userAgent);

function ConnectionStatus() {
  // TODO(T-032): reflect the real WebSocket state; the demo feed counts as connected.
  const connected = env.demoData;
  const label = connected ? "Live updates connected" : "Live updates not connected";
  return (
    <span className="grid size-10 place-items-center" title={label}>
      <span aria-hidden="true" className={connected ? "live-dot size-2 rounded-pill bg-moss-500" : "size-2 rounded-pill bg-ink-400"} />
      <span className="sr-only">{label}</span>
    </span>
  );
}

export function TopBar() {
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const user = useSession((state) => state.user);

  // Ctrl/⌘ K focuses search. Keyboard actions never animate (06 §8).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <header className="flex items-center gap-3 px-4 pb-2 pt-4 md:px-5 md:pt-5 xl:px-8 xl:pt-6">
      <form
        role="search"
        className="relative w-full max-w-[380px]"
        onSubmit={(event) => {
          event.preventDefault();
          const query = new FormData(event.currentTarget).get("q")?.toString().trim();
          if (query) navigate(`/findings?q=${encodeURIComponent(query)}`);
        }}
      >
        <Search
          size={16}
          aria-hidden="true"
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-500"
        />
        <input
          ref={inputRef}
          name="q"
          type="search"
          autoComplete="off"
          aria-label="Search customers, findings and records"
          placeholder="Search customers, findings, records…"
          className="glass-control h-10 w-full rounded-control pl-10 pr-16 text-body text-ink-900 transition-[background-color] duration-fast ease-out placeholder:text-ink-500 focus:bg-white/80 [&::-webkit-search-cancel-button]:hidden"
        />
        <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border border-ink-200 bg-white/70 px-1.5 font-sans text-caption text-ink-500 sm:block">
          {isApplePlatform ? "⌘K" : "Ctrl K"}
        </kbd>
      </form>

      <div className="ml-auto flex items-center gap-2">
        <ConnectionStatus />
        <IconLink to="/alerts" label="Alerts">
          <Bell size={18} strokeWidth={1.75} aria-hidden="true" />
        </IconLink>
        <IconLink to="/settings" label="Settings" className="max-md:hidden">
          <Settings size={18} strokeWidth={1.75} aria-hidden="true" />
        </IconLink>
        <Link
          to="/settings"
          aria-label="Your profile"
          className="rounded-pill transition-transform duration-press ease-out motion-safe:active:scale-[0.97]"
        >
          <Avatar name={user?.fullName ?? "Guest"} tone="user" />
        </Link>
      </div>
    </header>
  );
}
