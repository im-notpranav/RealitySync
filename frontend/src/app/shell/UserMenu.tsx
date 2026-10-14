import { LogOut, UserRound, Users } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { Avatar, Pill } from "../../components/ui";
import { useSignOut } from "../../features/auth/useSignOut";
import { cn } from "../../lib/cn";
import { humanize } from "../../lib/format";
import { hasRole, useSession } from "../../store/session";

const itemClass =
  "flex h-10 w-full items-center gap-3 rounded-control px-3 text-body text-ink-900 " +
  "transition-[background-color,transform] duration-press ease-out pointer:hover:bg-ink-100 " +
  "motion-safe:active:scale-[0.97]";

/**
 * Avatar menu in the top bar (06 §5): profile, users (admin), sign out.
 * A disclosure of links and one button, so Tab order is natural; Escape and outside clicks close it.
 */
export function UserMenu() {
  const user = useSession((state) => state.user);
  const isDemo = useSession((state) => state.isDemo);
  const signOut = useSignOut();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const { pathname, search } = useLocation();

  useEffect(() => setOpen(false), [pathname, search]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!user) return null;

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-label="Account menu"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
        className="rounded-pill transition-transform duration-press ease-out motion-safe:active:scale-[0.97]"
      >
        <Avatar name={user.fullName} tone="user" />
      </button>
      {open ? (
        <div
          id={panelId}
          role="group"
          aria-label="Account"
          className={cn(
            "absolute right-0 top-12 z-[60] w-64 origin-top-right rounded-card bg-paper p-1.5 shadow-raised",
            "motion-safe:animate-[pop-in_180ms_cubic-bezier(.23,1,.32,1)]",
          )}
        >
          <div className="flex items-center gap-3 px-3 pb-3 pt-2">
            <Avatar name={user.fullName} tone="user" size="sm" />
            <div className="min-w-0">
              <p className="truncate text-body font-medium text-ink-950">{user.fullName}</p>
              <p className="truncate text-caption text-ink-500">{user.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 pb-2">
            <Pill tone="neutral">{humanize(user.role)}</Pill>
            {isDemo ? <Pill tone="amber">Demo data</Pill> : null}
          </div>
          <div className="my-1 h-px bg-ink-100" aria-hidden="true" />
          <Link to="/settings" className={itemClass}>
            <UserRound size={16} aria-hidden="true" className="text-ink-500" />
            Profile
          </Link>
          {hasRole(user, "admin") ? (
            <Link to="/settings?tab=users" className={itemClass}>
              <Users size={16} aria-hidden="true" className="text-ink-500" />
              Users
            </Link>
          ) : null}
          <button
            type="button"
            className={itemClass}
            disabled={signingOut}
            onClick={() => {
              setSigningOut(true);
              void signOut();
            }}
          >
            <LogOut size={16} aria-hidden="true" className="text-ink-500" />
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
