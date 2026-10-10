import * as SelectPrimitive from "@radix-ui/react-select";
import * as SliderPrimitive from "@radix-ui/react-slider";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { Check, ChevronDown } from "lucide-react";
import { motion } from "motion/react";
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "../../lib/cn";

const controlBase =
  "h-10 w-full rounded-control px-3 text-body text-ink-900 transition-[background-color,border-color] duration-fast ease-out placeholder:text-ink-400";
const controlSurface = {
  paper: "border border-ink-200 bg-paper pointer:hover:border-ink-400",
  glass: "glass-control pointer:hover:bg-white/70",
} as const;

export function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-small font-medium text-ink-700">
        {label}
      </label>
      {children}
      {hint ? <p className="text-caption font-normal text-ink-500">{hint}</p> : null}
    </div>
  );
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  surface?: keyof typeof controlSurface;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { surface = "paper", className, ...props },
  ref,
) {
  return <input ref={ref} className={cn(controlBase, controlSurface[surface], className)} {...props} />;
});

// ------------------------------------------------------------------ select

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  label: string;
  surface?: keyof typeof controlSurface;
  className?: string;
  id?: string;
}

/** Popover scales from the trigger, exits faster (06 §8). */
export function Select({
  value,
  onValueChange,
  options,
  label,
  surface = "paper",
  className,
  id,
}: SelectProps) {
  return (
    <SelectPrimitive.Root value={value} onValueChange={onValueChange}>
      <SelectPrimitive.Trigger
        id={id}
        aria-label={label}
        className={cn(
          controlBase,
          controlSurface[surface],
          "inline-flex items-center justify-between gap-2 text-left",
          className,
        )}
      >
        <SelectPrimitive.Value />
        <SelectPrimitive.Icon>
          <ChevronDown size={16} className="text-ink-500" aria-hidden="true" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={6}
          className="popover-content z-[60] max-h-[var(--radix-select-content-available-height)] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-control bg-paper p-1 shadow-raised"
        >
          <SelectPrimitive.Viewport>
            {options.map((option) => (
              <SelectPrimitive.Item
                key={option.value}
                value={option.value}
                className="flex h-9 cursor-default select-none items-center justify-between gap-6 rounded-[8px] px-2.5 text-body text-ink-900 outline-none data-[highlighted]:bg-ink-100"
              >
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
                <SelectPrimitive.ItemIndicator>
                  <Check size={14} aria-hidden="true" />
                </SelectPrimitive.ItemIndicator>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}

// ------------------------------------------------------------------ switch & slider

export function Switch({
  checked,
  onCheckedChange,
  label,
  hideLabel,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  hideLabel?: boolean;
}) {
  const id = useId();
  return (
    <div className="inline-flex items-center gap-2.5">
      <SwitchPrimitive.Root
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        className="relative h-6 w-10 shrink-0 rounded-pill bg-ink-200 transition-colors duration-fast ease-out data-[state=checked]:bg-ink-950"
      >
        <SwitchPrimitive.Thumb className="block size-5 translate-x-0.5 rounded-pill bg-paper shadow-card transition-transform duration-base ease-out data-[state=checked]:translate-x-[18px]" />
      </SwitchPrimitive.Root>
      <label htmlFor={id} className={cn("text-small text-ink-700", hideLabel && "sr-only")}>
        {label}
      </label>
    </div>
  );
}

export function Slider({
  value,
  onValueChange,
  min = 0,
  max = 1,
  step = 0.05,
  label,
  format = (v: number) => v.toFixed(2),
}: {
  value: number;
  onValueChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label: string;
  format?: (value: number) => string;
}) {
  return (
    <div className="flex items-center gap-3">
      <SliderPrimitive.Root
        value={[value]}
        onValueChange={([next]) => onValueChange(next ?? value)}
        min={min}
        max={max}
        step={step}
        aria-label={label}
        className="relative flex h-5 w-full touch-none select-none items-center"
      >
        <SliderPrimitive.Track className="relative h-2 grow overflow-hidden rounded-pill bg-ink-200">
          <SliderPrimitive.Range className="absolute h-full rounded-pill bg-moss-500" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb className="block size-5 rounded-pill bg-paper shadow-card ring-1 ring-ink-200 transition-transform duration-press ease-out motion-safe:active:scale-110" />
      </SliderPrimitive.Root>
      <span className="min-w-12 whitespace-nowrap text-right text-small font-medium tabular text-ink-900">
        {format(value)}
      </span>
    </div>
  );
}

// ------------------------------------------------------------------ tabs

export const Tabs = TabsPrimitive.Root;
export const TabsContent = TabsPrimitive.Content;

/** Segmented control; the active segment slides between items (06 §8). */
export function TabsList({
  items,
  value,
  label,
  layoutId,
}: {
  items: { value: string; label: string }[];
  value: string;
  label: string;
  layoutId: string;
}) {
  return (
    <TabsPrimitive.List aria-label={label} className="inline-flex gap-1 rounded-control bg-ink-100 p-1">
      {items.map((item) => (
        <TabsPrimitive.Trigger
          key={item.value}
          value={item.value}
          className="relative h-8 rounded-[9px] px-3 text-small font-medium text-ink-500 transition-colors duration-fast data-[state=active]:text-ink-950"
        >
          {value === item.value ? (
            <motion.span
              layoutId={layoutId}
              className="absolute inset-0 rounded-[9px] bg-paper shadow-card"
              transition={{ type: "spring", duration: 0.3, bounce: 0 }}
            />
          ) : null}
          <span className="relative">{item.label}</span>
        </TabsPrimitive.Trigger>
      ))}
    </TabsPrimitive.List>
  );
}
