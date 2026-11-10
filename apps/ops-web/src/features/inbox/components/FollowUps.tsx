import { useId } from "react";
import { useTranslation } from "react-i18next";
import type { Application } from "@/features/applications";
import { daysAgo } from "../lib/dates";

export default function FollowUps({
  applications,
}: {
  applications: Application[];
}) {
  const { t } = useTranslation();
  const headingId = useId();
  const due = applications
    .flatMap(({ id, company, stage, applied_on }) =>
      stage === "applied" && applied_on
        ? [{ id, company, days: daysAgo(new Date(`${applied_on}T00:00`)) }]
        : [],
    )
    .filter(({ days }) => days >= 7)
    .sort((a, b) => b.days - a.days);

  if (due.length === 0) return null;

  return (
    <section
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex flex-col gap-2 rounded-xl border px-[18px] py-4"
    >
      <h2 id={headingId} className="text-ink m-0 text-[15px] font-semibold">
        {t("inbox.followUps")}
      </h2>
      {due.map(({ id, company, days }) => (
        <span key={id} className="flex flex-col">
          <span className="font-semibold">{company}</span>
          <span className="text-warn text-[13px]">
            {t("inbox.noReply", { days })}
          </span>
        </span>
      ))}
    </section>
  );
}
