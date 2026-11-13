import { useId } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { addDays, startOfDay } from "../lib/dates";
import type { CalendarItem } from "../lib/items";
import ItemBox from "./ItemBox";

interface ComingUpProps {
  items: CalendarItem[];
  onSelect: (stepId: string) => void;
}

export default function ComingUp({ items, onSelect }: ComingUpProps) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const now = new Date();
  const until = addDays(startOfDay(now), 14);
  const next = items
    .filter(
      (item) => item.kind !== "busy" && item.end >= now && item.start < until,
    )
    .slice(0, 6);

  return (
    <section
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex flex-col rounded-xl border px-5 py-[18px]"
    >
      <h2
        id={headingId}
        className="text-ink m-0 pb-2 text-[15px] font-semibold"
      >
        {t("calendar.comingUp")}
      </h2>
      {next.length === 0 && (
        <p className="text-ink-3 m-0 text-[14px]">
          {t("calendar.nothingComingUp")}
        </p>
      )}
      {next.map((item) => (
        <ItemBox
          key={item.id}
          item={item}
          onSelect={onSelect}
          className="border-hair-soft flex flex-col border-t py-2.5"
        >
          <span
            className={cn(
              "text-[13px] font-semibold",
              item.kind === "interview" ? "text-amber" : "text-ok",
            )}
          >
            {item.start.toLocaleString(
              i18n.language,
              item.allDay
                ? { weekday: "short", day: "numeric", month: "short" }
                : {
                    weekday: "short",
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                    hourCycle: "h23",
                  },
            )}
          </span>
          <span className="font-medium">
            {item.step
              ? t("calendar.task", { step: item.step, company: item.title })
              : item.title}
          </span>
        </ItemBox>
      ))}
    </section>
  );
}
