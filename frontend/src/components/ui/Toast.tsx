import * as ToastPrimitive from "@radix-ui/react-toast";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { create } from "zustand";

type ToastTone = "default" | "success" | "error" | "critical";

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  tone: ToastTone;
}

interface ToastState {
  toasts: ToastItem[];
  push: (toast: Omit<ToastItem, "id" | "tone"> & { tone?: ToastTone }) => void;
  dismiss: (id: number) => void;
}

let nextId = 1;

const useToasts = create<ToastState>((set) => ({
  toasts: [],
  push: (toast) => set((state) => ({ toasts: [...state.toasts, { tone: "default" as const, ...toast, id: nextId++ }].slice(-4) })),
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

/** `toast({ title: "Finding resolved" })` from anywhere. */
export const toast = (input: Parameters<ToastState["push"]>[0]) => useToasts.getState().push(input);

const icons = { default: Info, success: CheckCircle2, error: AlertTriangle, critical: AlertTriangle } as const;

/** Dark glass toasts, bottom-right; critical ones persist; swipe right to dismiss (06 §6, §8). */
export function Toaster() {
  const toasts = useToasts((state) => state.toasts);
  const dismiss = useToasts((state) => state.dismiss);

  return (
    <ToastPrimitive.Provider swipeDirection="right" duration={5000}>
      {toasts.map((item) => {
        const Icon = icons[item.tone];
        return (
          <ToastPrimitive.Root
            key={item.id}
            duration={item.tone === "critical" ? Infinity : 5000}
            onOpenChange={(open) => {
              if (!open) setTimeout(() => dismiss(item.id), 200);
            }}
            className="toast on-dark glass-dark relative flex w-[360px] max-w-[calc(100vw-32px)] gap-3 rounded-card p-4 pr-11 text-on-dark shadow-raised"
          >
            <Icon
              size={18}
              aria-hidden="true"
              className={item.tone === "success" ? "mt-0.5 shrink-0 text-moss-500" : "mt-0.5 shrink-0 text-on-dark-muted"}
            />
            <div className="min-w-0">
              <ToastPrimitive.Title className="text-body font-medium">{item.title}</ToastPrimitive.Title>
              {item.description ? (
                <ToastPrimitive.Description className="mt-0.5 text-small text-on-dark-muted">
                  {item.description}
                </ToastPrimitive.Description>
              ) : null}
            </div>
            <ToastPrimitive.Close
              aria-label="Dismiss"
              className="absolute right-3 top-3 grid size-7 place-items-center rounded-pill text-on-dark-muted transition-colors duration-fast pointer:hover:bg-white/10 pointer:hover:text-on-dark"
            >
              <X size={14} aria-hidden="true" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        );
      })}
      <ToastPrimitive.Viewport className="fixed bottom-20 right-3 z-[80] flex flex-col gap-2 outline-none md:bottom-4 md:right-4" />
    </ToastPrimitive.Provider>
  );
}
