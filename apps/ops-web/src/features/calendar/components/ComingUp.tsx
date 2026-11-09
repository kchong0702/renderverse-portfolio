import { useTranslation } from "react-i18next";
import Panel from "@/shared/components/Panel";
import { cn } from "@/shared/lib/cn";
import type { CalendarEvent } from "../api/calendar";
import { eventTime, isInterview } from "../lib/dates";

export default function ComingUp({ events }: { events: CalendarEvent[] }) {
  const { t, i18n } = useTranslation();
  const now = new Date();
  const next = events
    .filter((event) => eventTime(event.end, event.all_day) > now)
    .slice(0, 6);

  return (
    <Panel title={t("calendar.comingUp")} className="gap-3">
      {next.length === 0 && (
        <p className="text-ink-3 m-0 text-sm">
          {t("calendar.nothingComingUp")}
        </p>
      )}
      {next.map((event) => (
        <a
          key={event.id}
          href={event.url}
          target="_blank"
          rel="noreferrer"
          className="border-hair-soft flex flex-col border-t pt-3 no-underline first-of-type:border-t-0 first-of-type:pt-0"
        >
          <span className="text-ink-3 text-[13px]">
            {eventTime(event.start, event.all_day).toLocaleString(
              i18n.language,
              event.all_day
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
          <span
            className={cn(
              "font-medium",
              isInterview(event) ? "text-amber" : "text-ink",
            )}
          >
            {event.title || t("calendar.untitled")}
          </span>
        </a>
      ))}
    </Panel>
  );
}
