import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { isoDay } from "../lib/dates";
import { itemTone, onDay, type CalendarItem } from "../lib/items";
import ItemBox from "./ItemBox";

interface MonthGridProps {
  days: Date[];
  month: number;
  items: CalendarItem[];
  onSelect: (stepId: string) => void;
}

export default function MonthGrid({
  days,
  month,
  items,
  onSelect,
}: MonthGridProps) {
  const { t, i18n } = useTranslation();
  const today = isoDay(new Date());

  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[680px] grid-cols-7">
        {days.slice(0, 7).map((day) => (
          <span
            key={day.getTime()}
            className="text-ink-3 pb-2.5 text-center text-[13px] font-medium"
          >
            {day.toLocaleDateString(i18n.language, { weekday: "short" })}
          </span>
        ))}
        {days.map((day) => (
          <div
            key={day.getTime()}
            className="border-hair-soft flex min-h-[92px] min-w-0 flex-col gap-1 border-t border-l p-1.5"
          >
            <span
              className={cn(
                "text-[13px]",
                isoDay(day) === today
                  ? "text-ink font-bold"
                  : "text-ink-3 font-medium",
                day.getMonth() !== month && "opacity-50",
              )}
            >
              {day.getDate()}
            </span>
            {items
              .filter((item) => onDay(item, day))
              .map((item) => (
                <ItemBox
                  key={item.id}
                  item={item}
                  onSelect={onSelect}
                  className={cn(
                    "truncate rounded-md border px-1.5 text-[12px] font-semibold",
                    itemTone[item.kind],
                  )}
                >
                  {item.title || t("calendar.busy")}
                </ItemBox>
              ))}
          </div>
        ))}
      </div>
    </div>
  );
}
