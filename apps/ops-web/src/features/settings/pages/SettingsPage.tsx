import { useTranslation } from "react-i18next";
import PageBody from "@/shared/components/layout/PageBody";
import PageHeader from "@/shared/components/layout/PageHeader";
import StateMessage from "@/shared/components/ui/StateMessage";
import AutomationPanel from "../components/layout/AutomationPanel";
import ConnectionsPanel from "../components/layout/ConnectionsPanel";
import JobAgentPanel from "../components/layout/JobAgentPanel";
import SchedulingPanel from "../components/layout/SchedulingPanel";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";

export default function SettingsPage() {
  const { t } = useTranslation();
  const settings = useSettings();
  const update = useUpdateSettings();

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
        {settings.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : settings.isError ? (
          <StateMessage tone="error">
            {t("settings.loadFailed", { reason: settings.error.message })}
          </StateMessage>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(420px,100%),1fr))] items-start gap-6">
            <ConnectionsPanel connections={settings.data.connections} />
            <JobAgentPanel
              jobAgent={settings.data.job_agent}
              onChange={update.mutate}
            />
            <AutomationPanel
              automation={settings.data.automation}
              onChange={update.mutate}
            />
            <SchedulingPanel
              scheduling={settings.data.scheduling}
              aiProvider={settings.data.ai_provider}
              onChange={update.mutate}
            />
          </div>
        )}
      </PageBody>
    </>
  );
}
