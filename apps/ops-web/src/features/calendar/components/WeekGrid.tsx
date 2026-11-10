import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import type { CalendarEvent } from "../api/calendar";
import { addDays, eventTime, isoDay } from "../lib/dates";
import { isInterview } from "../lib/interview";

const HOUR_PX = 56;

const hourOf = (time: Date) => time.getHours() + time.getMinutes() / 60;

const clockHour = (time: string) => Number(time.slice(0, 2));

const toneClass = (event: CalendarEvent) =>
  isInterview(event)
    ? "bg-warn-bg border-amber text-ink"
    : "bg-chip border-hair text-ink-3";

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
  monday: Date;
  events: CalendarEvent[];
  workDayStart: string;
  workDayEnd: string;
}

export default function WeekGrid({
  monday,
  events,
  workDayStart,
  workDayEnd,
}: WeekGridProps) {
  const { t, i18n } = useTranslation();
  const days = Array.from({ length: 7 }, (_, index) => addDays(monday, index));
  const today = isoDay(new Date());
  const timed = events
    .filter((event) => !event.all_day)
    .map((event) => {
      const start = eventTime(event.start, false);
      const end = eventTime(event.end, false);
      return {
        event,
        day: isoDay(start),
        from: hourOf(start),
        to: isoDay(end) === isoDay(start) ? hourOf(end) : 24,
        label: start.toLocaleTimeString(i18n.language, {
          hour: "2-digit",
          minute: "2-digit",
          hourCycle: "h23",
        }),
      };
    });
  const allDay = events.filter((event) => event.all_day);
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
      <div className="grid min-w-[720px] grid-cols-[52px_repeat(7,minmax(0,1fr))] gap-y-2">
        <span />
        {days.map((day) => (
          <span
            key={day.getTime()}
            className={cn(
              "text-center text-sm",
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
            <span className="text-ink-3 text-xs">{t("calendar.allDay")}</span>
            {days.map((day) => (
              <span key={day.getTime()} className="flex flex-col gap-1 px-1">
                {allDay
                  .filter(
                    (event) =>
                      event.start <= isoDay(day) && isoDay(day) < event.end,
                  )
                  .map((event) => (
                    <a
                      key={event.id}
                      href={event.url}
                      target="_blank"
                      rel="noreferrer"
                      className={cn(
                        "truncate rounded-md border-l-[3px] px-2 py-0.5 text-xs font-semibold no-underline",
                        toneClass(event),
                      )}
                    >
                      {event.title || t("calendar.untitled")}
                    </a>
                  ))}
              </span>
            ))}
          </>
        )}
        <div className="relative" style={{ height: hours.length * HOUR_PX }}>
          {hours.map((hour) => (
            <span
              key={hour}
              className="text-ink-3 absolute text-xs"
              style={{ top: (hour - first) * HOUR_PX }}
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
              ({ event, from, to, label, column, columns }) => (
                <a
                  key={event.id}
                  href={event.url}
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    "absolute flex flex-col overflow-hidden rounded-md border-l-[3px] px-2 py-1 text-xs no-underline",
                    toneClass(event),
                  )}
                  style={{
                    top: (from - first) * HOUR_PX,
                    height: Math.max(36, (to - from) * HOUR_PX - 4),
                    left: `calc(${(100 * column) / columns}% + 4px)`,
                    width: `calc(${100 / columns}% - 8px)`,
                  }}
                >
                  <span className="truncate font-semibold">
                    {event.title || t("calendar.untitled")}
                  </span>
                  <span className="truncate">{label}</span>
                </a>
              ),
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
