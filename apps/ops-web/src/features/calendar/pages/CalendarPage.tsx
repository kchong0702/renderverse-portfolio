import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useApplications } from "@/features/applications";
import { GoogleNotice, useGoogleAccount } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import { cn } from "@/shared/lib/cn";
import AutomationPanel from "../components/AutomationPanel";
import ComingUp from "../components/ComingUp";
import MonthGrid from "../components/MonthGrid";
import WeekGrid from "../components/WeekGrid";
import { useEvents } from "../hooks/useEvents";
import {
  addDays,
  isoDay,
  mondayOf,
  monthDays,
  shiftAnchor,
  startOfDay,
} from "../lib/dates";
import { itemTone, itemsOf } from "../lib/items";

export default function CalendarPage() {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const [params, setParams] = useSearchParams();
  const [now, setNow] = useState(Date.now);
  const { settings, account, problem } = useGoogleAccount();
  const applications = useApplications();
  const view = params.get("view") === "month" ? "month" : "week";
  const asked = new Date(`${params.get("day")}T00:00`);
  const today = startOfDay(new Date());
  const anchor = isNaN(asked.getTime()) ? today : asked;
  const days =
    view === "month"
      ? monthDays(anchor)
      : Array.from({ length: 7 }, (_, index) =>
          addDays(mondayOf(anchor), index),
        );
  const events = useEvents(
    days[0],
    addDays(days[days.length - 1], 1),
    account !== null,
  );
  const upcoming = useEvents(today, addDays(today, 14), account !== null);
  const failed = events.error ?? upcoming.error;
  const minutes = Math.floor((now - events.dataUpdatedAt) / 60_000);
  const dayMonth = { day: "numeric", month: "long" } as const;

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);

  return (
    <>
      <PageHeader
        title={t("calendar.title")}
        subtitle={
          account &&
          events.isSuccess &&
          t("calendar.subtitle", {
            when:
              minutes < 1
                ? t("calendar.justNow")
                : new Intl.RelativeTimeFormat(i18n.language).format(
                    -minutes,
                    "minute",
                  ),
          })
        }
        actions={
          account && (
            <>
              <div
                role="group"
                aria-label={t("calendar.view.label")}
                className="bg-chip flex rounded-lg p-[3px]"
              >
                {(["week", "month"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={option === view}
                    onClick={() =>
                      setParams({
                        ...(option === "month" && { view: option }),
                        day: isoDay(anchor),
                      })
                    }
                    className={cn(
                      "min-h-[34px] cursor-pointer rounded-md px-3 text-[14px]",
                      option === view
                        ? "bg-panel text-ink shadow-card font-semibold"
                        : "text-ink-3 bg-transparent font-medium",
                    )}
                  >
                    {t(`calendar.view.${option}`)}
                  </button>
                ))}
              </div>
              <button
                type="button"
                aria-label={t(`calendar.previous.${view}`)}
                className={buttonClass()}
                onClick={() =>
                  setParams({
                    ...(view === "month" && { view }),
                    day: isoDay(shiftAnchor(anchor, view, -1)),
                  })
                }
              >
                <ChevronLeft aria-hidden size={16} />
              </button>
              <button
                type="button"
                className={buttonClass()}
                onClick={() => setParams(view === "month" ? { view } : {})}
              >
                {t("calendar.today")}
              </button>
              <button
                type="button"
                aria-label={t(`calendar.next.${view}`)}
                className={buttonClass()}
                onClick={() =>
                  setParams({
                    ...(view === "month" && { view }),
                    day: isoDay(shiftAnchor(anchor, view, 1)),
                  })
                }
              >
                <ChevronRight aria-hidden size={16} />
              </button>
            </>
          )
        }
      />
      <PageBody>
        {settings.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : settings.isError ? (
          <StateMessage tone="error">
            {t("calendar.loadFailed", { reason: settings.error.message })}
          </StateMessage>
        ) : account === null ? (
          <GoogleNotice problem={problem} next="/calendar" />
        ) : failed instanceof ApiError && failed.status === 409 ? (
          <GoogleNotice problem="expired" next="/calendar" />
        ) : (
          <div className="flex flex-wrap items-start gap-6">
            <section
              aria-labelledby={headingId}
              className="bg-panel border-hair shadow-card flex min-w-0 flex-[999_1_640px] flex-col gap-3.5 rounded-xl border px-[22px] py-5"
            >
              <div className="flex items-baseline justify-between">
                <h2
                  id={headingId}
                  className="text-ink m-0 text-[16px] font-semibold"
                >
                  {view === "month"
                    ? anchor.toLocaleDateString(i18n.language, {
                        month: "long",
                        year: "numeric",
                      })
                    : t("calendar.range", {
                        start:
                          days[0].getMonth() === days[6].getMonth()
                            ? String(days[0].getDate())
                            : days[0].toLocaleDateString(
                                i18n.language,
                                dayMonth,
                              ),
                        end: days[6].toLocaleDateString(
                          i18n.language,
                          dayMonth,
                        ),
                      })}
                </h2>
                <span className="text-ink-3 text-[13px]">
                  {t("calendar.workHours", {
                    start: settings.data.scheduling.work_day_start.slice(0, 5),
                    end: settings.data.scheduling.work_day_end.slice(0, 5),
                  })}
                </span>
              </div>
              {events.isPending || applications.isPending ? (
                <p className="text-ink-3 m-0 text-[14px]">
                  {t("common.loading")}
                </p>
              ) : events.isError ? (
                <StateMessage tone="error">
                  {t("calendar.loadFailed", { reason: events.error.message })}
                </StateMessage>
              ) : applications.isError ? (
                <StateMessage tone="error">
                  {t("applications.loadFailed", {
                    reason: applications.error.message,
                  })}
                </StateMessage>
              ) : view === "month" ? (
                <MonthGrid
                  days={days}
                  month={anchor.getMonth()}
                  items={itemsOf(events.data, applications.data)}
                />
              ) : (
                <WeekGrid
                  days={days}
                  items={itemsOf(events.data, applications.data)}
                  workDayStart={settings.data.scheduling.work_day_start}
                  workDayEnd={settings.data.scheduling.work_day_end}
                />
              )}
              <div className="text-ink-3 flex flex-wrap gap-[18px] text-[13px]">
                {(["interview", "task", "busy"] as const).map((kind) => (
                  <span key={kind} className="inline-flex items-center gap-1.5">
                    <span
                      className={cn(
                        "size-2.5 rounded-[3px] border",
                        itemTone[kind],
                      )}
                    />
                    {t(`calendar.legend.${kind}`)}
                  </span>
                ))}
              </div>
            </section>
            <aside className="flex max-w-[300px] min-w-0 flex-[1_1_260px] flex-col gap-4">
              {upcoming.isPending || applications.isPending ? (
                <StateMessage>{t("common.loading")}</StateMessage>
              ) : upcoming.isError ? (
                <StateMessage tone="error">
                  {t("calendar.loadFailed", { reason: upcoming.error.message })}
                </StateMessage>
              ) : applications.isError ? (
                <StateMessage tone="error">
                  {t("applications.loadFailed", {
                    reason: applications.error.message,
                  })}
                </StateMessage>
              ) : (
                <ComingUp items={itemsOf(upcoming.data, applications.data)} />
              )}
              <AutomationPanel
                followUpReminders={settings.data.automation.follow_up_reminders}
              />
            </aside>
          </div>
        )}
      </PageBody>
    </>
  );
}
