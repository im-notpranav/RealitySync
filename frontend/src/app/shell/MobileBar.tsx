import * as Dialog from "@radix-ui/react-dialog";
import { Menu } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { cn } from "../../lib/cn";
import { useSession } from "../../store/session";
import { adminNav, primaryNav, settingsNav, visibleEntries, type NavEntry } from "../nav";

const EASE_OUT = [0.23, 1, 0.32, 1] as const;
const EASE_DRAWER = [0.32, 0.72, 0, 1] as const;

const barItem =
  "relative flex flex-1 flex-col items-center justify-center gap-1 rounded-[20px] text-caption " +
  "transition-[color,transform] duration-press ease-out motion-safe:active:scale-[0.97]";

function BarItem({ entry }: { entry: NavEntry }) {
  const Icon = entry.icon;
  return (
    <NavLink
      to={entry.to}
      end={entry.end}
      className={({ isActive }) => cn(barItem, isActive ? "text-on-dark" : "text-on-dark-muted")}
    >
      {({ isActive }) => (
        <>
          {isActive ? (
            <motion.span
              layoutId="mobile-active"
              className="absolute inset-1 rounded-[18px] border border-white/15 bg-white/[0.12]"
              transition={{ type: "spring", duration: 0.3, bounce: 0 }}
            />
          ) : null}
          <Icon size={20} strokeWidth={1.75} className="relative" aria-hidden="true" />
          <span className="relative">{entry.label}</span>
        </>
      )}
    </NavLink>
  );
}

export function MobileBar() {
  const user = useSession((state) => state.user);
  const [moreOpen, setMoreOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => setMoreOpen(false), [pathname]);

  const all = [...visibleEntries(primaryNav, user), ...visibleEntries(adminNav, user)];
  const inBar = all.filter((entry) => entry.mobile);
  const inMore = [...all.filter((entry) => !entry.mobile), settingsNav];

  return (
    <nav
      aria-label="Primary"
      className="on-dark glass-dark fixed inset-x-2 bottom-2 z-20 flex h-16 items-stretch gap-1 rounded-panel p-1 text-on-dark md:hidden"
    >
      {inBar.map((entry) => (
        <BarItem key={entry.to} entry={entry} />
      ))}

      <Dialog.Root open={moreOpen} onOpenChange={setMoreOpen}>
        <Dialog.Trigger className={cn(barItem, "text-on-dark-muted")}>
          <Menu size={20} strokeWidth={1.75} aria-hidden="true" />
          <span>More</span>
        </Dialog.Trigger>
        <AnimatePresence>
          {moreOpen ? (
            <Dialog.Portal forceMount>
              <Dialog.Overlay asChild forceMount>
                <motion.div
                  className="fixed inset-0 z-30 bg-black/30"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1, transition: { duration: 0.24, ease: EASE_OUT } }}
                  exit={{ opacity: 0, transition: { duration: 0.2, ease: EASE_OUT } }}
                />
              </Dialog.Overlay>
              <Dialog.Content asChild forceMount aria-describedby={undefined}>
                {/* Sheet: enters on the drawer curve, leaves faster (06 §8). */}
                <motion.div
                  className="on-dark glass-dark fixed inset-x-2 bottom-2 z-40 rounded-panel p-3 text-on-dark"
                  initial={{ transform: "translateY(110%)" }}
                  animate={{ transform: "translateY(0%)", transition: { duration: 0.32, ease: EASE_DRAWER } }}
                  exit={{ transform: "translateY(110%)", transition: { duration: 0.2, ease: EASE_OUT } }}
                >
                  <Dialog.Title className="px-3 pb-2 pt-1 text-caption text-on-dark-muted">More</Dialog.Title>
                  <ul className="flex flex-col gap-1">
                    {inMore.map((entry) => {
                      const Icon = entry.icon;
                      return (
                        <li key={entry.to}>
                          <NavLink
                            to={entry.to}
                            className={({ isActive }) =>
                              cn(
                                "flex h-12 items-center gap-3 rounded-control px-3 text-body font-medium transition-transform duration-press ease-out motion-safe:active:scale-[0.97]",
                                isActive ? "bg-white/[0.12] text-on-dark" : "text-on-dark-muted",
                              )
                            }
                          >
                            <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
                            {entry.label}
                          </NavLink>
                        </li>
                      );
                    })}
                  </ul>
                </motion.div>
              </Dialog.Content>
            </Dialog.Portal>
          ) : null}
        </AnimatePresence>
      </Dialog.Root>
    </nav>
  );
}
