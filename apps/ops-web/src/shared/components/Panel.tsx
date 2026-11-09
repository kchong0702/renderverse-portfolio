import { useId, type ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

interface PanelProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function Panel({ title, children, className }: PanelProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className={cn(
        "bg-panel border-hair shadow-card flex flex-col gap-4 rounded-xl border px-[26px] py-6",
        className,
      )}
    >
      <h2 id={headingId} className="text-ink m-0 text-base font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}
