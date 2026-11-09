import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import AutomationPanel from "../components/AutomationPanel";
import ConnectionsPanel from "../components/ConnectionsPanel";
import JobAgentPanel from "../components/JobAgentPanel";
import SchedulingPanel from "../components/SchedulingPanel";
import SystemPanel from "../components/SystemPanel";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";

export default function SettingsPage() {
  const { t } = useTranslation();
  const settings = useSettings();
  const update = useUpdateSettings();
  const googleError = useSearchParams()[0].get("google_error");

  const saveStatus = update.isPending
    ? t("settings.save.saving")
    : update.isError
      ? t("settings.save.failed", { reason: update.error.message })
      : update.isSuccess
        ? t("settings.save.saved")
        : null;

  return (
    <>
      <PageHeader
        title={t("settings.title")}
        subtitle={t("settings.subtitle")}
        actions={
          saveStatus && (
            <span
              role="status"
              className={
                update.isError ? "text-crit text-sm" : "text-ink-3 text-sm"
              }
            >
              {saveStatus}
            </span>
          )
        }
      />
      <PageBody>
        {googleError && (
          <StateMessage tone="error">
            {t(
              `settings.connections.googleErrors.${googleError === "denied" || googleError === "scopes" ? googleError : "failed"}`,
            )}
          </StateMessage>
        )}
        {settings.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : settings.isError ? (
          <StateMessage tone="error">
            {t("settings.loadFailed", { reason: settings.error.message })}
          </StateMessage>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(420px,100%),1fr))] items-start gap-6">
            <div className="flex flex-col gap-6">
              <ConnectionsPanel connections={settings.data.connections} />
              <AutomationPanel
                automation={settings.data.automation}
                onChange={update.mutate}
              />
            </div>
            <div className="flex flex-col gap-6">
              <JobAgentPanel
                jobAgent={settings.data.job_agent}
                onChange={update.mutate}
              />
              <SchedulingPanel
                scheduling={settings.data.scheduling}
                onChange={update.mutate}
              />
              <SystemPanel
                aiModel={settings.data.ai_model}
                onChange={update.mutate}
              />
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}
