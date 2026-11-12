import { ChevronDown } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

interface SectionProps {
  title: string;
  hint: string;
  summary: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export default function Section({
  title,
  hint,
  summary,
  defaultOpen = false,
  children,
}: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const headingId = useId();

  return (
    <section
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex flex-col rounded-xl border"
    >
      <h2 className="m-0">
        <button
          type="button"
          id={headingId}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="text-ink flex w-full cursor-pointer items-center gap-3.5 px-4 py-4 text-left sm:px-[22px] sm:py-[18px]"
        >
          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="text-[17px] font-semibold">{title}</span>
            <span className="text-ink-3 text-sm font-normal">{hint}</span>
            <span className="text-ink-3 text-[13px] font-medium sm:hidden">
              {summary}
            </span>
          </span>
          <span className="text-ink-3 hidden text-[13px] font-medium whitespace-nowrap sm:inline">
            {summary}
          </span>
          <ChevronDown
            size={18}
            aria-hidden="true"
            className={cn(
              "text-ink-3 shrink-0 transition-transform",
              open && "rotate-180",
            )}
          />
        </button>
      </h2>
      {open && <div className="border-hair-soft border-t">{children}</div>}
    </section>
  );
}
