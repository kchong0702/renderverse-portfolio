import { useIsMutating } from "@tanstack/react-query";
import { Sparkle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import Segmented from "@/shared/components/Segmented";
import { cn } from "@/shared/lib/cn";
import StateMessage from "@/shared/components/StateMessage";
import { useSettings } from "@/features/settings";
import type { PostedWithin } from "../api/jobs";
import JobDetail from "../components/JobDetail";
import JobList from "../components/JobList";
import { useFindJobs, useJobs } from "../hooks/useJobs";
import { findJobsMutationOptions } from "../queries/jobs";

const TABS = ["picked", "saved"] as const;
type JobsTab = (typeof TABS)[number];
const POSTED_WITHIN: PostedWithin[] = ["week", "day", "month"];
const control =
  "border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 text-sm";

export default function JobsPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const jobs = useJobs();
  const find = useFindJobs();
  const agent = useSettings().data?.job_agent;
  const [search, setSearch] = useState<{
    query?: string;
    location?: string;
    posted_within: PostedWithin;
  }>({ posted_within: "week" });
  const query = search.query ?? agent?.query ?? "";
  const location = search.location ?? agent?.location ?? "";
  const run = () =>
    find.mutate({
      query: query.trim() || null,
      location: location.trim() || null,
      posted_within: search.posted_within,
    });
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
              onClick={run}
              className={buttonClass("primary")}
            >
              <Sparkle size={14} className="text-amber-soft" />
              {finding ? t("jobs.runningAgent") : t("jobs.runAgent")}
            </button>
          </>
        }
      />
      <PageBody>
        <form
          aria-label={t("jobs.search.label")}
          onSubmit={(event) => {
            event.preventDefault();
            run();
          }}
          className="bg-panel border-hair shadow-card flex flex-wrap items-center gap-2.5 rounded-xl border p-3"
        >
          <label className="flex flex-[2_1_240px]">
            <span className="sr-only">{t("jobs.search.keywords")}</span>
            <input
              type="text"
              maxLength={200}
              value={query}
              onChange={(event) =>
                setSearch({ ...search, query: event.target.value })
              }
              className={cn(control, "flex-1")}
            />
          </label>
          <label className="flex flex-[1_1_160px]">
            <span className="sr-only">{t("jobs.search.location")}</span>
            <input
              type="text"
              maxLength={200}
              value={location}
              onChange={(event) =>
                setSearch({ ...search, location: event.target.value })
              }
              className={cn(control, "flex-1")}
            />
          </label>
          <select
            aria-label={t("jobs.search.postedWithin")}
            value={search.posted_within}
            onChange={(event) =>
              setSearch({
                ...search,
                posted_within:
                  POSTED_WITHIN.find((name) => name === event.target.value) ??
                  "week",
              })
            }
            className={control}
          >
            {POSTED_WITHIN.map((name) => (
              <option key={name} value={name}>
                {t(`jobs.search.posted.${name}`)}
              </option>
            ))}
          </select>
          <Segmented
            label={t("jobs.tabs.label")}
            value={tab}
            options={TABS.map((name) => ({
              value: name,
              label: t(`jobs.tabs.${name}`),
            }))}
            onChange={(next) => setParams({ tab: next })}
          />
          <button
            type="submit"
            disabled={finding}
            className={buttonClass("primary")}
          >
            {t("jobs.search.submit")}
          </button>
        </form>
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
        ) : selected ? (
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
      </PageBody>
    </>
  );
}
