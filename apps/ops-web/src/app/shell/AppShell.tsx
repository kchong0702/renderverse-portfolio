import { useTranslation } from "react-i18next";
import { Outlet, useLocation } from "react-router-dom";
import { followUpDays, useApplications } from "@/features/applications";
import { AssistantDock } from "@/features/assistant";
import { useReplySuggestion } from "@/features/inbox";
import { useJobs } from "@/features/jobs";
import { navItemAt } from "./nav";
import Sidebar from "./Sidebar";

export default function AppShell() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const item = navItemAt(pathname);
  const [best, runnerUp] =
    useJobs().data?.jobs.filter((job) => job.status === "picked") ?? [];
  const followUp = useApplications().data?.find(
    (a) => followUpDays(a) !== null,
  );
  const reply = useReplySuggestion();
  const fixed = (
    item?.key === "jobs"
      ? [
          runnerUp &&
            t("assistant.suggestions.jobs.compare", {
              first: best.company,
              second: runnerUp.company,
            }),
          runnerUp &&
            t("assistant.suggestions.jobs.raiseFit", {
              title: runnerUp.title,
            }),
          t("assistant.suggestions.jobs.similar"),
        ].filter((suggestion) => suggestion !== undefined)
      : item?.key === "applications"
        ? [
            followUp &&
              t("assistant.suggestions.applications.followUp", {
                company: followUp.company,
              }),
            t("assistant.suggestions.applications.offers"),
            t("assistant.suggestions.applications.summary"),
          ].filter((suggestion) => suggestion !== undefined)
        : item
          ? t(`assistant.suggestions.${item.key}`, { returnObjects: true })
          : []
  ).map((text) => ({ label: text, text }));

  return (
    <div className="flex min-h-screen flex-wrap min-[792px]:h-screen min-[792px]:flex-nowrap">
      <Sidebar />
      <main className="flex min-w-0 flex-[999_1_560px] flex-col">
        <Outlet />
      </main>
      {pathname !== "/documents" && (
        <AssistantDock
          topic={item && t(`nav.items.${item.key}`)}
          suggestions={
            item?.key === "inbox" && reply ? [reply, ...fixed.slice(1)] : fixed
          }
        />
      )}
    </div>
  );
}
