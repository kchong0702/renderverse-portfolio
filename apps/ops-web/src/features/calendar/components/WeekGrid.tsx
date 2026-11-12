import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { isoDay } from "../lib/dates";
import { itemTone, onDay, type CalendarItem } from "../lib/items";
import ItemBox from "./ItemBox";

const HOUR_PX = 60;

const MIN_EVENT_PX = 50;

const hourOf = (time: Date) => time.getHours() + time.getMinutes() / 60;

const clockHour = (time: string) => Number(time.slice(0, 2));

function sideBySide<T extends { from: number; to: number }>(slots: T[]) {
  const placed: (T & { column: number; columns: number })[] = [];
  let cluster: typeof placed = [];
  let ends: number[] = [];
  for (const slot of [...slots].sort((a, b) => a.from - b.from)) {
    if (slot.from >= Math.max(...ends)) {
      cluster = [];
      ends = [];
    }
    const free = ends.findIndex((end) => end <= slot.from);
    const column = free === -1 ? ends.length : free;
    ends[column] = slot.to;
    const item = { ...slot, column, columns: 0 };
    cluster.push(item);
    placed.push(item);
    for (const member of cluster) member.columns = ends.length;
  }
  return placed;
}

interface WeekGridProps {
  days: Date[];
  items: CalendarItem[];
  workDayStart: string;
  workDayEnd: string;
  onSelect: (stepId: string) => void;
}

export default function WeekGrid({
  days,
  items,
  workDayStart,
  workDayEnd,
  onSelect,
}: WeekGridProps) {
  const { t, i18n } = useTranslation();
  const today = isoDay(new Date());
  const timed = items
    .filter((item) => !item.allDay)
    .map((item) => {
      const from = hourOf(item.start);
      return {
        item,
        day: isoDay(item.start),
        from,
        to: Math.max(
          isoDay(item.end) === isoDay(item.start) ? hourOf(item.end) : 24,
          from + MIN_EVENT_PX / HOUR_PX,
        ),
        label: [
          item.start.toLocaleTimeString(i18n.language, {
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
          }),
          item.step.toLocaleLowerCase(i18n.language),
        ]
          .filter(Boolean)
          .join(" "),
      };
    });
  const allDay = items.filter((item) => item.allDay);
  const first = Math.floor(
    Math.min(clockHour(workDayStart), ...timed.map(({ from }) => from)),
  );
  const last = Math.ceil(
    Math.max(clockHour(workDayEnd), ...timed.map(({ to }) => to)),
  );
  const hours = Array.from(
    { length: last - first },
    (_, index) => first + index,
  );

  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[680px] grid-cols-[52px_repeat(7,minmax(0,1fr))]">
        <span />
        {days.map((day) => (
          <span
            key={day.getTime()}
            className={cn(
              "pb-2.5 text-center text-[13px]",
              isoDay(day) === today
                ? "text-ink font-bold"
                : "text-ink-3 font-medium",
            )}
          >
            {day.toLocaleDateString(i18n.language, {
              weekday: "short",
              day: "numeric",
            })}
          </span>
        ))}
        {allDay.length > 0 && (
          <>
            <span className="text-ink-3 text-[12px]">
              {t("calendar.allDay")}
            </span>
            {days.map((day) => (
              <span
                key={day.getTime()}
                className="flex flex-col gap-1 px-1 pb-2.5"
              >
                {allDay
                  .filter((item) => onDay(item, day))
                  .map((item) => (
                    <ItemBox
                      key={item.id}
                      item={item}
                      onSelect={onSelect}
                      className={cn(
                        "truncate rounded-lg border px-2 py-0.5 text-[12px] font-semibold",
                        itemTone[item.kind],
                      )}
                    >
                      {item.title || t("calendar.busy")}
                    </ItemBox>
                  ))}
              </span>
            ))}
          </>
        )}
        <div className="flex flex-col">
          {hours.map((hour) => (
            <span
              key={hour}
              className="text-ink-3 h-[60px] -translate-y-2 text-[12px]"
            >
              {`${String(hour).padStart(2, "0")}:00`}
            </span>
          ))}
        </div>
        {days.map((day) => (
          <div
            key={day.getTime()}
            className="border-hair-soft relative border-l"
            style={{
              height: hours.length * HOUR_PX,
              backgroundImage:
                "linear-gradient(to bottom, var(--color-hair-soft) 1px, transparent 1px)",
              backgroundSize: `100% ${HOUR_PX}px`,
            }}
          >
            {sideBySide(timed.filter((slot) => slot.day === isoDay(day))).map(
              ({ item, from, to, label, column, columns }) => (
                <ItemBox
                  key={item.id}
                  item={item}
                  onSelect={onSelect}
                  className={cn(
                    "absolute overflow-hidden rounded-lg border px-2 py-1.5 text-[12px] leading-[1.35]",
                    itemTone[item.kind],
                  )}
                  style={{
                    top: (from - first) * HOUR_PX,
                    height: (to - from) * HOUR_PX - 4,
                    left: `calc(${(100 * column) / columns}% + 4px)`,
                    width: `calc(${100 / columns}% - 8px)`,
                  }}
                >
                  <div className="truncate font-semibold">
                    {item.title || t("calendar.busy")}
                  </div>
                  <div className="truncate">{label}</div>
                </ItemBox>
              ),
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
