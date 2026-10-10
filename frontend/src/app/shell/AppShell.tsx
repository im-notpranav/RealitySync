import { useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { MobileBar } from "./MobileBar";
import { Scene } from "./Scene";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

/** Scene → glass (sidebar, work panel) → paper (cards inside pages). 06 §5. */
export function AppShell() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();

  // Page navigation is instant (06 §8); just start each page at the top.
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [pathname]);

  return (
    <div className="relative isolate h-dvh overflow-hidden">
      <a
        href="#main-content"
        className="sr-only z-50 rounded-control bg-paper px-4 py-2 text-body font-medium text-ink-950 shadow-raised focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <Scene />
      <div className="relative flex h-full gap-3 p-2 md:p-3">
        <Sidebar />
        <main className="glass-panel flex min-w-0 flex-1 flex-col overflow-hidden rounded-panel shadow-panel">
          <TopBar />
          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            <div
              id="main-content"
              tabIndex={-1}
              className="mx-auto w-full max-w-content px-4 pb-28 outline-none md:px-5 md:pb-10 xl:px-8"
            >
              <Outlet />
            </div>
          </div>
        </main>
      </div>
      <MobileBar />
    </div>
  );
}
