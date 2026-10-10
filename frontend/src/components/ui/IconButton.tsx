import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";

import { cn } from "../../lib/cn";

export type IconButtonSurface = "glass" | "paper" | "dark";

interface IconStyle {
  surface?: IconButtonSurface;
  size?: "md" | "sm";
  className?: string;
}

const surfaces: Record<IconButtonSurface, string> = {
  glass: "glass-control text-ink-900 pointer:hover:bg-white/70",
  paper: "border border-ink-200 bg-paper text-ink-900 pointer:hover:bg-ink-100",
  dark: "bg-white/10 text-on-dark pointer:hover:bg-white/15",
};

function iconClasses({ surface = "glass", size = "md", className }: IconStyle) {
  return cn(
    "grid shrink-0 place-items-center rounded-pill transition-[transform,background-color] duration-press ease-out",
    "motion-safe:active:scale-[0.97]",
    size === "md" ? "size-10" : "size-8",
    surfaces[surface],
    className,
  );
}

export interface IconButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children">,
    Omit<IconStyle, "className"> {
  /** Required: icon buttons have no visible text (06 §10). Also used as the tooltip. */
  label: string;
  children: ReactNode;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, surface, size, className, type = "button", children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={iconClasses({ surface, size, className })}
      {...props}
    >
      {children}
    </button>
  );
});

export interface IconLinkProps extends Omit<LinkProps, "children">, Omit<IconStyle, "className"> {
  label: string;
  children: ReactNode;
}

export const IconLink = forwardRef<HTMLAnchorElement, IconLinkProps>(function IconLink(
  { label, surface, size, className, children, ...props },
  ref,
) {
  return (
    <Link
      ref={ref}
      aria-label={label}
      title={label}
      className={iconClasses({ surface, size, className: className as string | undefined })}
      {...props}
    >
      {children}
    </Link>
  );
});
