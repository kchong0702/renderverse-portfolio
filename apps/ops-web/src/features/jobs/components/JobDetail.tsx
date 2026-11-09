import { Bookmark, BookmarkCheck, ExternalLink, Send, X } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Badge, { type BadgeTone } from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import { relativeDay } from "@/shared/lib/dates";
import type { Job, Match } from "../api/jobs";
import { useUpdateJob } from "../hooks/useJobs";
import { fitTone } from "../lib/fit";

const MATCH_TONES: Record<Match, BadgeTone> = {
  met: "ok",
  partly: "warn",
  not_met: "crit",
};

const FIT_INK: Record<BadgeTone, string> = {
  ok: "text-ok",
  warn: "text-warn",
  neutral: "text-ink-3",
  accent: "text-amber",
  crit: "text-crit",
};

export default function JobDetail({ job }: { job: Job }) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const update = useUpdateJob();
  const { analysis } = job;
  const saved = job.status === "saved";

  return (
    <article
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex min-w-0 flex-[999_1_420px] flex-col gap-[22px] rounded-xl border px-[30px] py-7"
    >
      <div className="flex flex-wrap justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2
            id={headingId}
            className="m-0 text-[22px] leading-tight font-semibold"
          >
            {job.title}
          </h2>
          <span className="text-ink-2">
            {[job.company, job.location].filter(Boolean).join(" · ")}
          </span>
          <span className="text-ink-3 text-sm">
            {[
              job.salary || t("jobs.salaryNotStated"),
              job.posted_at &&
                t("jobs.posted", {
                  when: relativeDay(job.posted_at, i18n.language),
                }),
              job.source && t("jobs.via", { source: job.source }),
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </div>
        {analysis && (
          <div className="flex flex-col items-end">
            <span className={cn("text-[30px]", FIT_INK[fitTone(analysis.fit)])}>
              {analysis.fit}
            </span>
            <span className="text-ink-3 text-sm">
              {t(`jobs.bands.${analysis.band}`)}
            </span>
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-2.5">
        <Link
          to={`/applications?edit=new&job=${job.id}`}
          className={buttonClass("primary")}
        >
          <Send size={14} className="text-amber-soft" />
          {t("jobs.track")}
        </Link>
        <button
          type="button"
          aria-pressed={saved}
          onClick={() =>
            update.mutate({ id: job.id, status: saved ? "picked" : "saved" })
          }
          className={buttonClass()}
        >
          {saved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
          {saved ? t("jobs.saved") : t("jobs.save")}
        </button>
        <button
          type="button"
          onClick={() => update.mutate({ id: job.id, status: "dismissed" })}
          className={cn(buttonClass(), "text-ink-3")}
        >
          <X size={16} />
          {t("jobs.dismiss")}
        </button>
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className={cn(buttonClass(), "text-ink-3")}
          >
            <ExternalLink size={16} />
            {t("jobs.openPosting")}
          </a>
        )}
      </div>
      {update.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("jobs.updateFailed", { reason: update.error.message })}
        </p>
      )}
      <section className="flex flex-col">
        <div className="border-hair-soft flex flex-wrap items-baseline justify-between gap-x-4 border-b pb-2.5">
          <h3 className="text-ink m-0 text-base font-semibold">
            {t("jobs.requirements")}
          </h3>
          {analysis && (
            <span className="text-ink-3 text-sm">
              {(["met", "partly", "not_met"] as const)
                .map((match) =>
                  t(`jobs.matchCount.${match}`, {
                    count: analysis.requirements.filter(
                      (r) => r.match === match,
                    ).length,
                  }),
                )
                .join(" · ")}
            </span>
          )}
        </div>
        {analysis ? (
          analysis.requirements.map((requirement, index) => (
            <div
              key={index}
              className="border-hair-soft grid grid-cols-[88px_minmax(0,1fr)] items-start gap-4 border-b py-3.5"
            >
              <span className="flex justify-center">
                <Badge tone={MATCH_TONES[requirement.match]}>
                  {t(`jobs.match.${requirement.match}`)}
                </Badge>
              </span>
              <span className="flex flex-col">
                <span className="font-medium">{requirement.text}</span>
                <span className="text-ink-3 text-sm">
                  {[
                    requirement.reason,
                    requirement.importance === "nice_to_have" &&
                      t("jobs.niceToHave"),
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </span>
            </div>
          ))
        ) : (
          <p className="text-ink-3 m-0 py-3.5 text-sm">
            {t("jobs.notAnalysed")}
          </p>
        )}
      </section>
    </article>
  );
}
