import { Calendar } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  followUpDays,
  stepTitle,
  type Application,
  type Step,
} from "@/features/applications";
import type { Job } from "@/features/jobs";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import { relativeDay } from "@/shared/lib/dates";

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
  steps: Step[];
  jobs: Job[];
  picks: Job[];
}

export default function NextSteps({
  applications,
  steps,
  jobs,
  picks,
}: NextStepsProps) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const now = new Date();
  const active = applications.filter((a) => a.stage !== "closed");

  const rows: Row[] = [
    ...active.flatMap((a) =>
      a.overdue.flatMap((step) =>
        step.due_on
          ? [
              {
                key: step.id,
                when: relativeDay(step.due_on, i18n.language),
                whenInk: "text-warn",
                title: [a.company, stepTitle(step, t)].join(" · "),
                detail: a.role,
                action: {
                  label: t("dashboard.next.open"),
                  to: `/applications?edit=${a.id}`,
                },
              },
            ]
          : [],
      ),
    ),
    ...steps
      .flatMap((step) => {
        const a = active.find(({ id }) => id === step.application_id);
        return a && step.starts_at && step.status === "open"
          ? [{ a, step, at: new Date(step.starts_at) }]
          : [];
      })
      .map(({ a, step, at }) => {
        const gaps =
          jobs
            .find((job) => job.id === a.job_id)
            ?.analysis?.requirements.filter((r) => r.match === "not_met")
            .length ?? 0;
        const interview = a.stage === "interview";
        return {
          key: step.id,
          when: new Intl.DateTimeFormat(i18n.language, {
            weekday: "short",
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
          }).format(at),
          whenInk: at <= now ? "text-warn" : "text-amber",
          title: [a.company, stepTitle(step, t)].join(" · "),
          detail: [
            a.role,
            [
              step.format && t(`dashboard.next.formats.${step.format}`),
              step.location,
            ]
              .filter(Boolean)
              .join(", "),
            interview && gaps > 0 && t("dashboard.next.gaps", { count: gaps }),
          ]
            .filter(Boolean)
            .join(" · "),
          action:
            interview && gaps > 0
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
              action: {
                label: t("dashboard.next.draftEmail"),
                to: `/inbox?followUp=${a.id}`,
              },
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
