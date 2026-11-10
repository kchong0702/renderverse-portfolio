import { ChevronLeft, ChevronRight } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { GoogleNotice, useSettings } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import ComingUp from "../components/ComingUp";
import WeekGrid from "../components/WeekGrid";
import { useEvents } from "../hooks/useEvents";
import { addDays, isoDay, mondayOf, startOfDay } from "../lib/dates";

export default function CalendarPage() {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const [params, setParams] = useSearchParams();
  const settings = useSettings();
  const google = settings.data?.connections.find(({ id }) => id === "google");
  const account = google?.status === "connected" ? google.account : null;
  const asked = new Date(`${params.get("week")}T00:00`);
  const monday = mondayOf(isNaN(asked.getTime()) ? new Date() : asked);
  const today = startOfDay(new Date());
  const events = useEvents(monday, addDays(monday, 7), account !== null);
  const upcoming = useEvents(today, addDays(today, 14), account !== null);
  const failed = events.error ?? upcoming.error;

  return (
    <>
      <PageHeader
        title={t("calendar.title")}
        subtitle={account && t("calendar.subtitle", { account })}
        actions={
          account && (
            <>
              <button
                type="button"
                aria-label={t("calendar.previousWeek")}
                className={buttonClass()}
                onClick={() => setParams({ week: isoDay(addDays(monday, -7)) })}
              >
                <ChevronLeft aria-hidden size={16} />
              </button>
              <button
                type="button"
                className={buttonClass()}
                onClick={() => setParams({})}
              >
                {t("calendar.today")}
              </button>
              <button
                type="button"
                aria-label={t("calendar.nextWeek")}
                className={buttonClass()}
                onClick={() => setParams({ week: isoDay(addDays(monday, 7)) })}
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
          <GoogleNotice
            problem={
              google?.status === "not_configured"
                ? "not_configured"
                : "not_connected"
            }
            next="/calendar"
          />
        ) : failed instanceof ApiError && failed.status === 409 ? (
          <GoogleNotice problem="expired" next="/calendar" />
        ) : (
          <div className="flex flex-wrap items-start gap-4">
            <section
              aria-labelledby={headingId}
              className="bg-panel border-hair shadow-card flex min-w-0 flex-[999_1_640px] flex-col gap-4 rounded-xl border px-[26px] py-6"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 id={headingId} className="m-0 text-base font-semibold">
                  {new Intl.DateTimeFormat(i18n.language, {
                    day: "numeric",
                    month: "long",
                  }).formatRange(monday, addDays(monday, 6))}
                </h2>
                <span className="text-ink-3 text-sm">
                  {t("calendar.workHours", {
                    start: settings.data.scheduling.work_day_start.slice(0, 5),
                    end: settings.data.scheduling.work_day_end.slice(0, 5),
                  })}
                </span>
              </div>
              {events.isPending ? (
                <p className="text-ink-3 m-0 text-sm">{t("common.loading")}</p>
              ) : events.isError ? (
                <StateMessage tone="error">
                  {t("calendar.loadFailed", { reason: events.error.message })}
                </StateMessage>
              ) : (
                <WeekGrid
                  monday={monday}
                  events={events.data}
                  workDayStart={settings.data.scheduling.work_day_start}
                  workDayEnd={settings.data.scheduling.work_day_end}
                />
              )}
              <div className="text-ink-3 flex flex-wrap gap-5 text-[13px]">
                <span className="flex items-center gap-2">
                  <span className="bg-warn-bg border-amber size-3 rounded-sm border-l-[3px]" />
                  {t("calendar.legend.interview")}
                </span>
                <span className="flex items-center gap-2">
                  <span className="bg-chip border-hair size-3 rounded-sm border-l-[3px]" />
                  {t("calendar.legend.other")}
                </span>
              </div>
            </section>
            <aside className="flex min-w-0 flex-[1_1_260px] flex-col gap-4">
              {upcoming.isPending ? (
                <StateMessage>{t("common.loading")}</StateMessage>
              ) : upcoming.isError ? (
                <StateMessage tone="error">
                  {t("calendar.loadFailed", { reason: upcoming.error.message })}
                </StateMessage>
              ) : (
                <ComingUp events={upcoming.data} />
              )}
            </aside>
          </div>
        )}
      </PageBody>
    </>
  );
}
