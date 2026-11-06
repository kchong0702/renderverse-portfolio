import { cn } from "@/shared/lib/cn";

export type ButtonVariant = "primary" | "secondary";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-primary text-on-primary",
  secondary: "border-hair bg-panel text-ink border",
};

/** Classes for a button, or for a link drawn as one */
export function buttonClass(variant: ButtonVariant = "secondary"): string {
  return cn(
    "inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold no-underline disabled:cursor-default disabled:opacity-60",
    variants[variant],
  );
}
