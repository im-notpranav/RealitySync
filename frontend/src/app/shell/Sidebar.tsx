import { LogOut, Plus } from "lucide-react";
import { motion } from "motion/react";
import { Link, NavLink } from "react-router-dom";

import { ButtonLink } from "../../components/ui";
import { useSignOut } from "../../features/auth/useSignOut";
import { cn } from "../../lib/cn";
import { hasRole, useSession } from "../../store/session";
import { adminNav, primaryNav, settingsNav, visibleEntries, type NavEntry } from "../nav";
import { LogoMark } from "./Logo";

const itemBase =
  "group relative flex h-10 items-center gap-3 rounded-control px-3 text-body font-medium " +
  "transition-[color,background-color,transform] duration-press ease-out motion-safe:active:scale-[0.97] " +
  "max-xl:justify-center max-xl:px-0";

function SidebarItem({ entry }: { entry: NavEntry }) {
  const Icon = entry.icon;
  return (
    <NavLink
      to={entry.to}
      end={entry.end}
      title={entry.label}
      className={({ isActive }) =>
        cn(
          itemBase,
          isActive
            ? "text-on-dark"
            : "text-on-dark-muted pointer:hover:bg-white/5 pointer:hover:text-on-dark",
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive ? (
            // One shared indicator slides between items (06 §8: spatial consistency).
            <motion.span
              layoutId="sidebar-active"
              className="absolute inset-0 rounded-control border border-white/15 bg-white/[0.12] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
              transition={{ type: "spring", duration: 0.3, bounce: 0 }}
            />
          ) : null}
          <Icon size={20} strokeWidth={1.75} className="relative shrink-0" aria-hidden="true" />
          <span className="relative truncate max-xl:sr-only">{entry.label}</span>
        </>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  const user = useSession((state) => state.user);
  const signOut = useSignOut();
  const primary = visibleEntries(primaryNav, user);
  const admin = visibleEntries(adminNav, user);

  return (
    <aside className="on-dark glass-dark hidden w-[72px] shrink-0 flex-col rounded-panel p-3 text-on-dark md:flex xl:w-[248px]">
      <Link
        to="/"
        className="flex h-12 items-center gap-3 rounded-control px-2 max-xl:justify-center max-xl:px-0 xl:px-3"
      >
        <LogoMark className="shrink-0" />
        <span className="text-[17px] font-semibold tracking-[-0.02em] max-xl:sr-only">RealitySync</span>
      </Link>

      <nav aria-label="Primary" className="mt-6 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {primary.map((entry) => (
          <SidebarItem key={entry.to} entry={entry} />
        ))}
        {admin.length > 0 ? (
          <>
            <p className="mb-1 mt-5 px-3 text-caption text-on-dark-muted max-xl:hidden">Admin</p>
            <div aria-hidden="true" className="mx-3 my-3 h-px bg-white/10 xl:hidden" />
            {admin.map((entry) => (
              <SidebarItem key={entry.to} entry={entry} />
            ))}
          </>
        ) : null}
      </nav>

      <div className="mt-4 flex flex-col gap-1 border-t border-white/10 pt-4">
        <SidebarItem entry={settingsNav} />
        <button
          type="button"
          title="Sign out"
          onClick={() => void signOut()}
          className={cn(itemBase, "text-on-dark-muted pointer:hover:bg-white/5 pointer:hover:text-on-dark")}
        >
          <LogOut size={20} strokeWidth={1.75} className="shrink-0" aria-hidden="true" />
          <span className="max-xl:sr-only">Sign out</span>
        </button>
        {hasRole(user, "analyst") ? (
          <ButtonLink
            to="/investigations?new=1"
            variant="primary"
            title="New investigation"
            className="mt-3 w-full border border-white/10 max-xl:px-0"
          >
            <Plus size={16} aria-hidden="true" />
            <span className="max-xl:sr-only">New investigation</span>
          </ButtonLink>
        ) : null}
      </div>
    </aside>
  );
}
