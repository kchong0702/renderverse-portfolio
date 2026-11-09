import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

interface StateMessageProps {
  tone?: "neutral" | "error";
  children: ReactNode;
}

export default function StateMessage({
  tone = "neutral",
  children,
}: StateMessageProps) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "m-0 rounded-xl border px-[26px] py-6 text-sm",
        tone === "error"
          ? "border-crit/30 bg-crit-bg text-crit"
          : "border-hair bg-panel text-ink-3",
      )}
    >
      {children}
    </p>
  );
}
