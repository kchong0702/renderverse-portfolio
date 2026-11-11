import { useMutationState } from "@tanstack/react-query";
import { Sparkle } from "lucide-react";
import { useEffect, useId } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useFollowTurn } from "@/features/assistant";
import { useEditorStore } from "@/features/documents";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import { relativeDay } from "@/shared/lib/dates";
import type { Job, Match } from "../api/jobs";
import { useAnalyseJob, useTailorJob, useUpdateJob } from "../hooks/useJobs";
import { BAND_TONES, FIT_INK } from "../lib/fit";
import { analyseJobMutationOptions } from "../queries/jobs";

const MATCH_CHIP: Record<Match, string> = {
  met: "bg-ok-bg text-ok",
  partly: "bg-warn-bg text-warn",
  not_met: "bg-crit-bg text-crit",
};

export default function JobDetail({ job }: { job: Job }) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const requirementsId = useId();
  const update = useUpdateJob();
  const { mutate: markSeen } = useUpdateJob();
  const analyse = useAnalyseJob();
  const tailor = useTailorJob();
  const follow = useFollowTurn();
  const showPanel = useEditorStore((state) => state.showPanel);
  const navigate = useNavigate();
  const analysing = useMutationState({
    filters: {
      mutationKey: analyseJobMutationOptions.mutationKey,
      status: "pending",
    },
    select: (mutation) => mutation.state.variables,
  }).includes(job.id);
  const analyseFailed = analyse.isError
    ? analyse.error.message
    : analyse.data?.status === "failed"
      ? analyse.data.reason
      : null;
  const { analysis } = job;
  const saved = job.status === "saved";

  useEffect(() => {
    if (!job.seen_at) markSeen({ id: job.id, seen: true });
  }, [job.id, job.seen_at, markSeen]);

  return (
    <article
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex min-w-0 flex-[999_1_420px] flex-col gap-[22px] rounded-xl border px-[30px] py-7"
    >
      <div className="flex flex-wrap justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2
            id={headingId}
            className="m-0 text-[22px] leading-[1.3] font-semibold"
          >
            {job.title}
          </h2>
          <span className="text-ink-2">
            {[job.company, job.location].filter(Boolean).join(" · ")}
          </span>
          <span className="text-ink-3 text-sm">
            {[
              job.salary || t("jobs.salaryNotStated"),
              [
                job.posted_at &&
                  t("jobs.posted", {
                    when: relativeDay(job.posted_at, i18n.language),
                  }),
                job.source && t("jobs.via", { source: job.source }),
              ]
                .filter(Boolean)
                .join(" "),
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </div>
        {analysis && (
          <div className="flex flex-col items-end">
            <span
              className={cn("text-[30px]", FIT_INK[BAND_TONES[analysis.band]])}
            >
              {analysis.fit}
            </span>
            <span className="text-ink-3 text-sm">
              {t(`jobs.bands.${analysis.band}`)}
            </span>
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-2.5">
        <button
          type="button"
          disabled={tailor.isPending}
          onClick={() =>
            tailor.mutate(job.id, {
              onSuccess: ({ resume, cover_letter }) => {
                for (const copy of [resume, cover_letter])
                  if (copy?.tailoring)
                    follow.mutate({ kind: "document", id: copy.document_id });
                showPanel("assistant");
                navigate(`/documents?doc=${resume.document_id}`);
              },
            })
          }
          className={buttonClass("primary")}
        >
          <Sparkle size={14} className="text-amber-soft" />
          {tailor.isPending ? t("jobs.tailoring") : t("jobs.tailor")}
        </button>
        <button
          type="button"
          aria-pressed={saved}
          onClick={() =>
            update.mutate({ id: job.id, status: saved ? "picked" : "saved" })
          }
          className={buttonClass()}
        >
          {saved ? t("jobs.saved") : t("jobs.save")}
        </button>
        <button
          type="button"
          onClick={() => update.mutate({ id: job.id, status: "dismissed" })}
          className={buttonClass("muted")}
        >
          {t("jobs.dismiss")}
        </button>
        <button
          type="button"
          disabled={!job.url || analysing}
          title={job.url ? undefined : t("jobs.noPostingUrl")}
          onClick={() => analyse.mutate(job.id)}
          className={buttonClass()}
        >
          {analysing
            ? t("jobs.analysing")
            : analysis
              ? t("jobs.analyseAgain")
              : t("jobs.analyse")}
        </button>
      </div>
      {tailor.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("jobs.tailorFailed", { reason: tailor.error.message })}
        </p>
      )}
      {analyseFailed && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("jobs.analyseFailed", { reason: analyseFailed })}
        </p>
      )}
      {update.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("jobs.updateFailed", { reason: update.error.message })}
        </p>
      )}
      <section aria-labelledby={requirementsId} className="flex flex-col">
        <div className="border-hair-soft flex flex-wrap items-baseline justify-between gap-x-4 border-b pb-2.5">
          <h3
            id={requirementsId}
            className="text-ink m-0 text-base font-semibold"
          >
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
              <span
                className={cn(
                  "rounded-md py-0.5 text-center text-[13px] font-semibold",
                  MATCH_CHIP[requirement.match],
                )}
              >
                {t(`jobs.match.${requirement.match}`)}
              </span>
              <span className="flex flex-col">
                <span className="font-medium">{requirement.text}</span>
                <span className="text-ink-3 text-sm">{requirement.reason}</span>
              </span>
            </div>
          ))
        ) : (
          <p role="status" className="text-ink-3 m-0 py-3.5 text-sm">
            {analysing ? t("jobs.analysingNote") : t("jobs.notAnalysed")}
          </p>
        )}
      </section>
    </article>
  );
}
