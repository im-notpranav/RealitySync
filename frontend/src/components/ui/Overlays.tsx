import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import { EASE_DRAWER, EASE_OUT } from "../../lib/motion";
import { IconButton } from "./IconButton";

// ------------------------------------------------------------------ tooltip

/** 400 ms delay on first hover; neighbours open instantly within 300 ms (06 §8). */
export function TooltipProvider({ children }: { children: ReactNode }) {
  return (
    <TooltipPrimitive.Provider delayDuration={400} skipDelayDuration={300}>
      {children}
    </TooltipPrimitive.Provider>
  );
}

export function Tooltip({
  content,
  children,
  side = "top",
}: {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
}) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          collisionPadding={8}
          className="tooltip-content z-[70] max-w-xs rounded-[8px] bg-ink-950 px-2.5 py-1.5 text-caption text-on-dark shadow-raised"
        >
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

// ------------------------------------------------------------------ dialog

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  className?: string;
}

function Scrim() {
  return (
    <motion.div
      className="fixed inset-0 z-40 bg-black/25"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, transition: { duration: 0.2 } }}
      exit={{ opacity: 0, transition: { duration: 0.15 } }}
    />
  );
}

/** Centered dialog: scale 0.96 → 1 from the center, 200 ms (06 §8). */
export function Dialog({ open, onOpenChange, title, description, children, footer, className }: DialogProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open ? (
          <DialogPrimitive.Portal forceMount>
            <DialogPrimitive.Overlay asChild forceMount>
              <Scrim />
            </DialogPrimitive.Overlay>
            <div className="pointer-events-none fixed inset-0 z-50 grid place-items-center p-4">
              <DialogPrimitive.Content
                asChild
                forceMount
                {...(description ? {} : { "aria-describedby": undefined })}
              >
                <motion.div
                  className={cn(
                    "pointer-events-auto w-full max-w-[480px] rounded-card bg-paper p-6 shadow-raised outline-none",
                    className,
                  )}
                  initial={{ opacity: 0, transform: "scale(0.96)" }}
                  animate={{
                    opacity: 1,
                    transform: "scale(1)",
                    transition: { duration: 0.2, ease: EASE_OUT },
                  }}
                  exit={{
                    opacity: 0,
                    transform: "scale(0.96)",
                    transition: { duration: 0.15, ease: EASE_OUT },
                  }}
                >
                  <DialogPrimitive.Title className="text-h2 text-ink-950">{title}</DialogPrimitive.Title>
                  {description ? (
                    <DialogPrimitive.Description className="mt-1.5 text-small text-ink-500">
                      {description}
                    </DialogPrimitive.Description>
                  ) : null}
                  {children ? <div className="mt-5">{children}</div> : null}
                  {footer ? <div className="mt-6 flex justify-end gap-2">{footer}</div> : null}
                </motion.div>
              </DialogPrimitive.Content>
            </div>
          </DialogPrimitive.Portal>
        ) : null}
      </AnimatePresence>
    </DialogPrimitive.Root>
  );
}

// ------------------------------------------------------------------ drawer

export interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  /** Accessible name when `title` is not plain text. */
  label: string;
  header?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

/** Right-side sheet on the drawer curve; exits faster than it enters (06 §8). */
export function Drawer({ open, onOpenChange, title, label, header, children, footer }: DrawerProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open ? (
          <DialogPrimitive.Portal forceMount>
            <DialogPrimitive.Overlay asChild forceMount>
              <Scrim />
            </DialogPrimitive.Overlay>
            <DialogPrimitive.Content asChild forceMount aria-describedby={undefined}>
              <motion.div
                className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[560px] flex-col bg-paper shadow-raised outline-none sm:inset-y-2 sm:right-2 sm:rounded-card"
                initial={{ transform: "translateX(104%)" }}
                animate={{ transform: "translateX(0%)", transition: { duration: 0.32, ease: EASE_DRAWER } }}
                exit={{ transform: "translateX(104%)", transition: { duration: 0.2, ease: EASE_OUT } }}
              >
                <div className="flex items-start gap-3 border-b border-ink-100 px-6 pb-4 pt-5">
                  <div className="min-w-0 flex-1">
                    <DialogPrimitive.Title aria-label={label} className="text-h2 text-ink-950">
                      {title}
                    </DialogPrimitive.Title>
                    {header ? <div className="mt-3">{header}</div> : null}
                  </div>
                  <DialogPrimitive.Close asChild>
                    <IconButton label="Close" surface="paper" size="sm">
                      <X size={16} aria-hidden="true" />
                    </IconButton>
                  </DialogPrimitive.Close>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-5">{children}</div>
                {footer ? (
                  <div className="flex flex-wrap justify-end gap-2 border-t border-ink-100 px-6 py-4">
                    {footer}
                  </div>
                ) : null}
              </motion.div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        ) : null}
      </AnimatePresence>
    </DialogPrimitive.Root>
  );
}
