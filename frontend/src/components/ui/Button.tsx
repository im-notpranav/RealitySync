import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Link, type LinkProps } from "react-router-dom";

import { cn } from "../../lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "destructive";
/** Secondary buttons look different on glass (panel) and on paper (cards), 06 §6. */
export type ButtonSurface = "glass" | "paper";
export type ButtonSize = "md" | "sm";

interface ButtonStyle {
  variant?: ButtonVariant;
  surface?: ButtonSurface;
  size?: ButtonSize;
  className?: string;
}

const base =
  "inline-flex shrink-0 select-none items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium " +
  "transition-[transform,background-color,color,box-shadow,filter] duration-press ease-out " +
  "motion-safe:active:scale-[0.97] disabled:pointer-events-none disabled:opacity-45";

const sizes: Record<ButtonSize, string> = {
  md: "h-10 px-4 text-body",
  sm: "h-8 px-3 text-small",
};

const variants: Record<Exclude<ButtonVariant, "secondary">, string> = {
  primary: "bg-ink-950 text-on-dark shadow-button pointer:hover:bg-ink-700",
  ghost: "text-ink-900 pointer:hover:bg-ink-100",
  danger: "bg-rose-bg text-rose-fg pointer:hover:brightness-95",
  destructive: "bg-rose-fg text-paper pointer:hover:brightness-110",
};

const secondary: Record<ButtonSurface, string> = {
  glass: "glass-control text-ink-900 pointer:hover:bg-white/70",
  paper: "border border-ink-200 bg-paper text-ink-900 pointer:hover:bg-ink-100",
};

export function buttonClasses({ variant = "secondary", surface = "glass", size = "md", className }: ButtonStyle) {
  return cn(base, sizes[size], variant === "secondary" ? secondary[surface] : variants[variant], className);
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, Omit<ButtonStyle, "className"> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, surface, size, className, type = "button", ...props },
  ref,
) {
  return (
    <button ref={ref} type={type} className={buttonClasses({ variant, surface, size, className })} {...props} />
  );
});

export interface ButtonLinkProps extends LinkProps, Omit<ButtonStyle, "className"> {}

export const ButtonLink = forwardRef<HTMLAnchorElement, ButtonLinkProps>(function ButtonLink(
  { variant, surface, size, className, ...props },
  ref,
) {
  return (
    <Link
      ref={ref}
      className={buttonClasses({ variant, surface, size, className: className as string | undefined })}
      {...props}
    />
  );
});
