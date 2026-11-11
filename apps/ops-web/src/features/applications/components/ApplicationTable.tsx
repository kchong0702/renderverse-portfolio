import { useTranslation } from "react-i18next";
import { fitTone } from "@/features/jobs";
import Badge from "@/shared/components/Badge";
import type { Application } from "../api/applications";
import NextStep from "./NextStep";

const columns =
  "grid grid-cols-[minmax(0,1fr)_96px_48px] items-center gap-3 sm:grid-cols-[minmax(0,1fr)_120px_minmax(0,1fr)_56px] sm:gap-4";

interface ApplicationTableProps {
  applications: Application[];
  onEdit: (id: string) => void;
}

export default function ApplicationTable({
  applications,
  onEdit,
}: ApplicationTableProps) {
  const { t } = useTranslation();

  return (
    <div
      role="table"
      aria-label={t("applications.views.table")}
      className="bg-panel border-hair shadow-card overflow-hidden rounded-xl border"
    >
      <div
        role="row"
        className={`${columns} border-hair text-ink-3 border-b px-5 py-3 text-[13px] font-semibold`}
      >
        <span role="columnheader">{t("applications.table.application")}</span>
        <span role="columnheader">{t("applications.table.stage")}</span>
        <span role="columnheader" className="hidden sm:block">
          {t("applications.table.next")}
        </span>
        <span role="columnheader" className="text-right">
          {t("applications.table.fit")}
        </span>
      </div>
      {applications.map((application) => (
        <div
          key={application.id}
          role="row"
          className={`${columns} border-hair-soft border-b px-5 py-4 last:border-b-0`}
        >
          <span role="cell" className="flex min-w-0 flex-col gap-0.5">
            <button
              type="button"
              aria-label={t("applications.edit", { name: application.company })}
              onClick={() => onEdit(application.id)}
              className="text-ink cursor-pointer text-left font-semibold hover:underline"
            >
              {application.company}
            </button>
            <span className="text-ink-2 text-sm">{application.role}</span>
          </span>
          <span role="cell">
            <Badge>{t(`applications.stages.${application.stage}`)}</Badge>
          </span>
          <span role="cell" className="hidden text-sm sm:block">
            <NextStep application={application} />
          </span>
          <span role="cell" className="flex justify-end">
            {application.fit !== null && (
              <Badge tone={fitTone(application.fit)}>{application.fit}</Badge>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
