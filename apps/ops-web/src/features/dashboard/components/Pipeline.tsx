import { useId } from "react";
import { useTranslation } from "react-i18next";
import type { Application } from "@/features/applications";
import { cn } from "@/shared/lib/cn";
import { hasReached, lastEightWeeks } from "../lib/pipeline";

interface PipelineProps {
  applications: Application[];
  sent: Application[];
  saved: number;
}

export default function Pipeline({ applications, sent, saved }: PipelineProps) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const funnel = [
    { label: t("dashboard.pipeline.saved"), count: saved },
    { label: t("applications.stages.applied"), count: sent.length },
    ...(["replied", "interview", "offer"] as const).map((stage) => ({
      label: t(`applications.stages.${stage}`),
      count: sent.filter((a) => hasReached(a, stage)).length,
    })),
  ];
  const widest = Math.max(1, ...funnel.map((row) => row.count));
  const weeks = lastEightWeeks(applications);
  const tallest = Math.max(1, ...weeks.map((week) => week.sent));

  return (
    <section
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card grid grid-cols-[repeat(auto-fit,minmax(min(320px,100%),1fr))] gap-12 rounded-xl border px-7 py-6"
    >
      <div className="flex flex-col gap-3.5">
        <h2 id={headingId} className="text-ink m-0 text-base font-semibold">
          {t("dashboard.pipeline.title")}
        </h2>
        {funnel.map((row, index) => (
          <div
            key={row.label}
            className="grid grid-cols-[84px_minmax(0,1fr)_36px] items-center gap-3"
          >
            <span className="text-ink-2">{row.label}</span>
            <div className="bg-hair-soft h-2 rounded">
              <div
                className={cn(
                  "h-2 rounded",
                  index === funnel.length - 1 ? "bg-ok" : "bg-ink",
                )}
                style={{
                  width: `${Math.max(3, Math.round((row.count / widest) * 100))}%`,
                }}
              />
            </div>
            <span className="text-right">{row.count}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-ink m-0 text-base font-semibold">
            {t("dashboard.weeks.title")}
          </h2>
          <span className="text-ink-3 inline-flex items-center gap-1.5 text-sm">
            <span className="bg-ink size-2 rounded-xs" />
            {t("dashboard.weeks.applied")}
          </span>
        </div>
        <div
          role="img"
          aria-label={t("dashboard.weeks.chart", {
            counts: weeks.map((week) => week.sent).join(", "),
          })}
          className="border-hair flex h-[130px] items-end gap-2.5 border-b"
        >
          {weeks.map((week) => (
            <div
              key={week.start.toISOString()}
              className="flex h-full flex-1 items-end justify-center"
            >
              <div
                className="bg-ink w-[38%] rounded-t-xs"
                style={{ height: `${(week.sent / tallest) * 100}%` }}
              />
            </div>
          ))}
        </div>
        <div className="text-ink-3 flex gap-2.5 text-sm">
          {weeks.map((week, index) => (
            <span key={week.start.toISOString()} className="flex-1 text-center">
              {new Intl.DateTimeFormat(
                i18n.language,
                index === 0 || week.start.getDate() <= 7
                  ? { day: "numeric", month: "short" }
                  : { day: "numeric" },
              ).format(week.start)}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
