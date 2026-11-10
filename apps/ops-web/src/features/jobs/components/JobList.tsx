import { useTranslation } from "react-i18next";
import Badge from "@/shared/components/Badge";
import { cn } from "@/shared/lib/cn";
import { relativeDay } from "@/shared/lib/dates";
import type { Job } from "../api/jobs";
import { BAND_TONES } from "../lib/fit";

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
            {job.analysis ? (
              <Badge tone={BAND_TONES[job.analysis.band]}>
                {job.analysis.fit}
              </Badge>
            ) : (
              <Badge>{t("jobs.notScored")}</Badge>
            )}
          </button>
        </li>
      ))}
    </ul>
  );
}
