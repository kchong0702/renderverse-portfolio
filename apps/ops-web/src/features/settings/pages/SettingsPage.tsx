import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { usePreferences, useUpdatePreferences } from "@/features/preferences";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import AutomationPanel from "../components/AutomationPanel";
import ConnectionsPanel from "../components/ConnectionsPanel";
import JobAgentPanel from "../components/JobAgentPanel";
import SignInMethodsPanel from "../components/SignInMethodsPanel";
import SchedulingPanel from "../components/SchedulingPanel";
import SystemPanel from "../components/SystemPanel";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";

export default function SettingsPage() {
  const { t } = useTranslation();
  const settings = useSettings();
  const update = useUpdateSettings();
  const preferences = usePreferences();
  const updatePreferences = useUpdatePreferences();
  const params = useSearchParams()[0];
  const googleError = params.get("google_error");
  const linkError = params.get("link_error");

  const failed = [settings, preferences].find((query) => query.isError);
  const saves = [update, updatePreferences];
  const saveFailed = saves.find((save) => save.isError)?.error;
  const saveStatus = saves.some((save) => save.isPending)
    ? t("settings.save.saving")
    : saveFailed
      ? t("settings.save.failed", { reason: saveFailed.message })
      : saves.some((save) => save.isSuccess)
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
                saveFailed ? "text-crit text-sm" : "text-ink-3 text-sm"
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
        {linkError && (
          <StateMessage tone="error">
            {t(
              `settings.signInMethods.linkErrors.${linkError === "taken" || linkError === "unverified" ? linkError : "failed"}`,
            )}
          </StateMessage>
        )}
        {failed?.error ? (
          <StateMessage tone="error">
            {t("settings.loadFailed", { reason: failed.error.message })}
          </StateMessage>
        ) : !settings.data || !preferences.data ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(420px,100%),1fr))] items-start gap-6">
            <div className="flex flex-col gap-6">
              <ConnectionsPanel connections={settings.data.connections} />
              <SignInMethodsPanel />
              <AutomationPanel
                automation={settings.data.automation}
                onChange={update.mutate}
              />
            </div>
            <div className="flex flex-col gap-6">
              <JobAgentPanel
                preferences={preferences.data}
                onChange={updatePreferences.mutate}
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
