import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import Segmented from "@/shared/components/Segmented";
import StateMessage from "@/shared/components/StateMessage";
import JobDetail from "../components/JobDetail";
import JobList from "../components/JobList";
import { useJobs } from "../hooks/useJobs";

const TABS = ["picked", "saved"] as const;
type JobsTab = (typeof TABS)[number];

export default function JobsPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const jobs = useJobs();
  const tab: JobsTab =
    TABS.find((name) => name === params.get("tab")) ?? "picked";
  const shown = jobs.data?.filter((job) => job.status === tab) ?? [];
  const selected =
    shown.find((job) => job.id === params.get("posting")) ?? shown[0];

  return (
    <>
      <PageHeader
        title={t("jobs.title")}
        subtitle={t("jobs.subtitle")}
        actions={
          <Link to="/settings" className={buttonClass()}>
            {t("jobs.agentSchedule")}
          </Link>
        }
      />
      <PageBody>
        {jobs.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : jobs.isError ? (
          <StateMessage tone="error">
            {t("jobs.loadFailed", { reason: jobs.error.message })}
          </StateMessage>
        ) : (
          <>
            <Segmented
              label={t("jobs.tabs.label")}
              value={tab}
              options={TABS.map((name) => ({
                value: name,
                label: t(`jobs.tabs.${name}`, {
                  count: jobs.data.filter((job) => job.status === name).length,
                }),
              }))}
              onChange={(next) => setParams({ tab: next })}
            />
            {selected ? (
              <div className="flex flex-wrap items-start gap-4">
                <JobList
                  jobs={shown}
                  selectedId={selected.id}
                  onSelect={(id) => setParams({ tab, posting: id })}
                />
                <JobDetail key={selected.id} job={selected} />
              </div>
            ) : (
              <StateMessage>{t(`jobs.empty.${tab}`)}</StateMessage>
            )}
          </>
        )}
      </PageBody>
    </>
  );
}
