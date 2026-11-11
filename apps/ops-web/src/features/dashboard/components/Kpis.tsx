import { useTranslation } from "react-i18next";
import { isStepDue, type Application } from "@/features/applications";
import { cn } from "@/shared/lib/cn";
import { dayMonth, daysLeftThisWeek } from "@/shared/lib/dates";
import { daysAgo, hasReached, sentSince } from "../lib/pipeline";

interface KpisProps {
  applications: Application[];
  sent: Application[];
  days: number | null;
}

export default function Kpis({ applications, sent, days }: KpisProps) {
  const { t, i18n } = useTranslation();
  const replied = sent.filter((a) => hasReached(a, "replied")).length;
  const interviews = sent.filter((a) => hasReached(a, "interview")).length;
  const offers = sent.filter((a) => hasReached(a, "offer"));
  const nextOffer = offers.find((a) => a.next_step_due)?.next_step_due;

  const kpis = [
    {
      label: t("dashboard.kpis.applications"),
      value: sent.length,
      note:
        days === null
          ? t("dashboard.kpis.drafts", {
              count: applications.filter((a) => a.stage === "draft").length,
            })
          : t("dashboard.kpis.change", {
              change: new Intl.NumberFormat(i18n.language, {
                signDisplay: "exceptZero",
              }).format(
                sent.length -
                  (sentSince(applications, daysAgo(2 * days)).length -
                    sent.length),
              ),
              days,
            }),
      ink: "text-ink",
    },
    {
      label: t("dashboard.kpis.responseRate"),
      value: new Intl.NumberFormat(i18n.language, { style: "percent" }).format(
        sent.length ? replied / sent.length : 0,
      ),
      note: t("dashboard.kpis.replies", { count: replied, sent: sent.length }),
      ink: "text-ink",
    },
    {
      label: t("dashboard.kpis.interviews"),
      value: interviews,
      note: t("dashboard.kpis.thisWeek", {
        count: sent.filter(
          (a) => a.stage === "interview" && isStepDue(a, daysLeftThisWeek()),
        ).length,
      }),
      ink: "text-amber",
    },
    {
      label: t("dashboard.kpis.offers"),
      value: offers.length,
      note:
        nextOffer &&
        t("dashboard.kpis.decideBy", {
          when: dayMonth(new Date(`${nextOffer}T00:00`), i18n.language),
        }),
      ink: "text-ok",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 shell:grid-cols-[repeat(auto-fit,minmax(210px,1fr))] shell:gap-4">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="bg-panel border-hair shadow-card flex flex-col gap-0.5 rounded-xl border px-4 py-3.5 shell:gap-1.5 shell:px-[22px] shell:py-5"
        >
          <span className="text-ink-3 text-[13px] font-medium shell:text-sm">
            {kpi.label}
          </span>
          <span
            className={cn(
              "text-[26px] tracking-[-0.02em] shell:text-[30px]",
              kpi.ink,
            )}
          >
            {kpi.value}
          </span>
          {kpi.note && (
            <span className="text-ink-3 text-xs shell:text-sm">{kpi.note}</span>
          )}
        </div>
      ))}
    </div>
  );
}
