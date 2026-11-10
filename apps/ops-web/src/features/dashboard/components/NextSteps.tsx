import { Calendar } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  followUpDays,
  isStepDue,
  type Application,
} from "@/features/applications";
import type { Job } from "@/features/jobs";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import { daysLeftThisWeek, relativeDay } from "@/shared/lib/dates";

interface Row {
  key: string;
  when: string;
  whenInk: string;
  title: string;
  detail: string;
  action?: { label: string; to: string };
}

interface NextStepsProps {
  applications: Application[];
  jobs: Job[];
  picks: Job[];
}

export default function NextSteps({
  applications,
  jobs,
  picks,
}: NextStepsProps) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const rows: Row[] = [
    ...applications
      .filter((a) => isStepDue(a, daysLeftThisWeek()))
      .sort((a, b) => a.next_step_at.localeCompare(b.next_step_at))
      .map((a) => {
        const at = new Date(a.next_step_at);
        const gaps =
          jobs
            .find((job) => job.id === a.job_id)
            ?.analysis?.requirements.filter((r) => r.match === "not_met")
            .length ?? 0;
        const interview = a.stage === "interview";
        return {
          key: a.id,
          when:
            at < today
              ? relativeDay(a.next_step_at, i18n.language)
              : new Intl.DateTimeFormat(i18n.language, {
                  weekday: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                  hourCycle: "h23",
                }).format(at),
          whenInk: at < today ? "text-warn" : "text-amber",
          title: [a.company, a.next_step].filter(Boolean).join(" · "),
          detail: [
            a.role,
            [
              a.next_step_format &&
                t(`dashboard.next.formats.${a.next_step_format}`),
              a.next_step_location,
            ]
              .filter(Boolean)
              .join(", "),
            interview && gaps > 0 && t("dashboard.next.gaps", { count: gaps }),
          ]
            .filter(Boolean)
            .join(" · "),
          action: interview
            ? { label: t("dashboard.next.prepare"), to: "/documents" }
            : {
                label: t("dashboard.next.open"),
                to: `/applications?edit=${a.id}`,
              },
        };
      }),
    ...applications.flatMap((a) => {
      const days = followUpDays(a);
      return days === null
        ? []
        : [
            {
              key: a.id,
              when: t("dashboard.next.days", { count: days }),
              whenInk: "text-warn",
              title: t("dashboard.next.followUp", { company: a.company }),
              detail: t("dashboard.next.noReply"),
            },
          ];
    }),
    ...picks.slice(0, 3).map((job) => ({
      key: job.id,
      when: t("dashboard.next.new"),
      whenInk: "text-ok",
      title: [job.company, job.title].filter(Boolean).join(" · "),
      detail: t("dashboard.next.fromAgent", { fit: job.analysis?.fit }),
      action: {
        label: t("dashboard.next.review"),
        to: `/jobs?posting=${job.id}`,
      },
    })),
  ];

  return (
    <section
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card rounded-xl border px-7 py-6"
    >
      <div className="border-hair-soft flex items-center justify-between gap-3 border-b pb-3.5">
        <h2
          id={headingId}
          className="text-ink m-0 flex items-center gap-2 text-base font-semibold"
        >
          <Calendar size={15} className="text-amber" />
          {t("dashboard.next.title")}
        </h2>
        <span className="text-ink-3 text-sm">
          {t("dashboard.next.count", { count: rows.length })}
        </span>
      </div>
      {rows.length === 0 ? (
        <p className="text-ink-3 m-0 pt-4 text-sm">
          {t("dashboard.next.empty")}
        </p>
      ) : (
        rows.map((row) => (
          <div
            key={row.key}
            className="border-hair-soft flex items-center gap-5 border-b py-4"
          >
            <span className={cn("min-w-[88px] text-sm", row.whenInk)}>
              {row.when}
            </span>
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="font-semibold">{row.title}</span>
              <span className="text-ink-3 text-sm">{row.detail}</span>
            </span>
            {row.action && (
              <Link to={row.action.to} className={buttonClass()}>
                {row.action.label}
              </Link>
            )}
          </div>
        ))
      )}
    </section>
  );
}
