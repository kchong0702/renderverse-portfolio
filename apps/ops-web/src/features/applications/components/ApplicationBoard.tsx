import { useTranslation } from "react-i18next";
import { FIT_INK, fitTone } from "@/features/jobs";
import { cn } from "@/shared/lib/cn";
import type { Application } from "../api/applications";
import { STAGES } from "../lib/stages";
import NextStep from "./NextStep";

interface ApplicationBoardProps {
  applications: Application[];
  onEdit: (id: string) => void;
}

export default function ApplicationBoard({
  applications,
  onEdit,
}: ApplicationBoardProps) {
  const { t } = useTranslation();

  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[980px] grid-cols-5 items-start gap-3.5">
        {STAGES.filter((stage) => stage !== "closed").map((stage) => {
          const cards = applications.filter((a) => a.stage === stage);
          return (
            <section
              key={stage}
              aria-label={t(`applications.stages.${stage}`)}
              className="bg-hair-soft flex flex-col gap-2.5 rounded-xl p-3"
            >
              <h2 className="text-ink m-0 flex justify-between px-1 pt-1 pb-1.5 text-base font-semibold">
                {t(`applications.stages.${stage}`)}
                <span className="text-ink-3">{cards.length}</span>
              </h2>
              {cards.map((application) => (
                <button
                  key={application.id}
                  type="button"
                  aria-label={t("applications.edit", {
                    name: application.company,
                  })}
                  onClick={() => onEdit(application.id)}
                  className="bg-panel border-hair shadow-card text-ink flex cursor-pointer flex-col gap-1 rounded-xl border p-4 text-left"
                >
                  <span className="flex w-full justify-between gap-2">
                    <span className="font-semibold">{application.company}</span>
                    {application.fit !== null && (
                      <span
                        className={cn(
                          "text-[12px]",
                          FIT_INK[fitTone(application.fit)],
                        )}
                      >
                        {application.fit}
                      </span>
                    )}
                  </span>
                  <span className="text-ink-2 text-[13px]">
                    {application.role}
                  </span>
                  <NextStep
                    application={application}
                    className="mt-2 text-[12px]"
                  />
                </button>
              ))}
            </section>
          );
        })}
      </div>
    </div>
  );
}
