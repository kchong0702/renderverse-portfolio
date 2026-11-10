import { useIsMutating } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import Segmented from "@/shared/components/Segmented";
import StateMessage from "@/shared/components/StateMessage";
import JobDetail from "../components/JobDetail";
import JobList from "../components/JobList";
import { useFindJobs, useJobs } from "../hooks/useJobs";
import { findJobsMutationOptions } from "../queries/jobs";

const TABS = ["picked", "saved"] as const;
type JobsTab = (typeof TABS)[number];

export default function JobsPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const jobs = useJobs();
  const find = useFindJobs();
  const finding =
    useIsMutating({ mutationKey: findJobsMutationOptions.mutationKey }) > 0;
  const tab: JobsTab =
    TABS.find((name) => name === params.get("tab")) ?? "picked";
  const shown = jobs.data?.jobs.filter((job) => job.status === tab) ?? [];
  const selected =
    shown.find((job) => job.id === params.get("posting")) ?? shown[0];

  return (
    <>
      <PageHeader
        title={t("jobs.title")}
        subtitle={t("jobs.subtitle")}
        actions={
          <>
            <Link to="/settings" className={buttonClass()}>
              {t("jobs.agentSchedule")}
            </Link>
            <button
              type="button"
              disabled={finding}
              onClick={() => find.mutate()}
              className={buttonClass("primary")}
            >
              <Sparkles size={16} className="text-amber-soft" />
              {finding ? t("jobs.runningAgent") : t("jobs.runAgent")}
            </button>
          </>
        }
      />
      <PageBody>
        {finding ? (
          <p role="status" className="text-ink-3 m-0 text-sm">
            {t("jobs.runningNote")}
          </p>
        ) : find.isError ? (
          <p role="alert" className="text-crit m-0 text-sm">
            {t("jobs.runFailed", { reason: find.error.message })}
          </p>
        ) : find.data?.status === "failed" ? (
          <p role="alert" className="text-crit m-0 text-sm">
            {t("jobs.runFailed", { reason: find.data.reason })}
          </p>
        ) : (
          find.data && (
            <p role="status" className="text-ink-3 m-0 text-sm">
              {t("jobs.found", { count: find.data.reply.length })}
            </p>
          )
        )}
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
                label: t(`jobs.tabs.${name}`),
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
