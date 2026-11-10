import { Sparkle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { useApplications } from "@/features/applications";
import { useJobs } from "@/features/jobs";
import { useSettings } from "@/features/settings";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import Segmented from "@/shared/components/Segmented";
import StateMessage from "@/shared/components/StateMessage";
import Kpis from "../components/Kpis";
import NextSteps from "../components/NextSteps";
import Pipeline from "../components/Pipeline";
import ShortcutCards from "../components/ShortcutCards";
import {
  PERIODS,
  PERIOD_DAYS,
  daysAgo,
  sentSince,
  type Period,
} from "../lib/pipeline";

export default function DashboardPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const applications = useApplications();
  const jobs = useJobs();
  const settings = useSettings();
  const period: Period =
    PERIODS.find((name) => name === params.get("period")) ?? "30d";
  const days = PERIOD_DAYS[period];
  const newPicks =
    jobs.data?.jobs.filter(
      (job) =>
        job.status === "picked" &&
        !job.seen_at &&
        ["good", "excellent"].includes(job.analysis?.band ?? ""),
    ) ?? [];
  const sent = sentSince(
    applications.data ?? [],
    days === null ? null : daysAgo(days),
  );

  return (
    <>
      <PageHeader
        title={t("nav.items.dashboard")}
        subtitle={t(`dashboard.subtitle.${period}`)}
        actions={
          <>
            <Segmented
              label={t("dashboard.periods.label")}
              value={period}
              options={PERIODS.map((name) => ({
                value: name,
                label: t(`dashboard.periods.${name}`),
              }))}
              onChange={(next) => setParams({ period: next })}
            />
            <Link
              to="/applications?edit=new"
              className={buttonClass("primary")}
            >
              <Sparkle size={14} className="text-amber-soft" />
              {t("dashboard.newApplication")}
            </Link>
          </>
        }
      />
      <PageBody>
        {applications.isError || jobs.isError ? (
          <StateMessage tone="error">
            {t("dashboard.loadFailed", {
              reason: (applications.error ?? jobs.error)?.message,
            })}
          </StateMessage>
        ) : !applications.data || !jobs.data ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : (
          <>
            <Kpis applications={applications.data} sent={sent} days={days} />
            <Pipeline
              applications={applications.data}
              sent={sent}
              saved={
                jobs.data.jobs.filter((job) => job.status === "saved").length
              }
            />
            <NextSteps
              applications={applications.data}
              jobs={jobs.data.jobs}
              picks={newPicks}
            />
            <ShortcutCards settings={settings.data} />
          </>
        )}
      </PageBody>
    </>
  );
}
