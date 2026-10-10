import type { Variants } from "motion/react";
import { useEffect, useState } from "react";

/** 06 §8 easing tokens as cubic-bezier arrays for Motion. */
export const EASE_OUT = [0.23, 1, 0.32, 1] as const;
export const EASE_IN_OUT = [0.77, 0, 0.175, 1] as const;
export const EASE_DRAWER = [0.32, 0.72, 0, 1] as const;

const pending = new Map<string, boolean>();

function storedOnce(key: string): boolean {
  try {
    const storageKey = `rs-anim:${key}`;
    if (sessionStorage.getItem(storageKey)) return false;
    sessionStorage.setItem(storageKey, "1");
  } catch {
    // Storage unavailable (private mode, tests): animate once per page load instead.
  }
  return true;
}

/**
 * True only for the first visit of `key` in this browser session — the single orchestrated load
 * moment of 06 §8. Stable for the lifetime of the mounted component (safe under StrictMode).
 */
export function useFirstVisit(key: string): boolean {
  const [first] = useState(() => {
    if (!pending.has(key)) pending.set(key, storedOnce(key));
    return pending.get(key)!;
  });
  useEffect(() => () => void pending.set(key, false), [key]);
  return first;
}

/** Parent: stagger children 40 ms apart (06 §8 first load). */
export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};

/** Child: fade + rise 8 px. Uses a transform string so it stays on the compositor. */
export const rise: Variants = {
  hidden: { opacity: 0, transform: "translateY(8px)" },
  show: { opacity: 1, transform: "translateY(0px)", transition: { duration: 0.3, ease: EASE_OUT } },
};
