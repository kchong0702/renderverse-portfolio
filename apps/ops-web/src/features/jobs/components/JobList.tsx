import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { relativeDay } from "@/shared/lib/dates";
import type { Job } from "../api/jobs";
import { BAND_TONES, type FitTone } from "../lib/fit";

const FIT_CHIP: Record<FitTone, string> = {
  ok: "bg-ok-bg text-ok",
  warn: "bg-warn-bg text-warn",
  neutral: "bg-chip text-ink-3",
};

interface JobListProps {
  jobs: Job[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function JobList({ jobs, selectedId, onSelect }: JobListProps) {
  const { t, i18n } = useTranslation();

  return (
    <ul
      aria-label={t("jobs.postings")}
      className="m-0 flex max-w-[400px] flex-[1_1_300px] list-none flex-col gap-2 p-0"
    >
      {jobs.map((job) => (
        <li key={job.id}>
          <button
            type="button"
            aria-pressed={job.id === selectedId}
            onClick={() => onSelect(job.id)}
            className={cn(
              "bg-panel text-ink shadow-card flex w-full cursor-pointer items-start gap-3.5 rounded-xl border p-[18px] text-left",
              job.id === selectedId ? "border-amber" : "border-hair",
            )}
          >
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="font-semibold">{job.title}</span>
              <span className="text-ink-3 text-sm">
                {[job.company, job.location].filter(Boolean).join(" · ")}
              </span>
              {job.posted_at && (
                <span className="text-ink-3 text-sm">
                  {t("jobs.posted", {
                    when: relativeDay(job.posted_at, i18n.language),
                  })}
                </span>
              )}
            </span>
            <span
              className={cn(
                "rounded-md px-2 py-0.5 text-[13px] whitespace-nowrap",
                FIT_CHIP[
                  job.analysis ? BAND_TONES[job.analysis.band] : "neutral"
                ],
              )}
            >
              {job.analysis ? job.analysis.fit : t("jobs.notScored")}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
