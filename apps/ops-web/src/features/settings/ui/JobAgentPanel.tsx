import { useTranslation } from "react-i18next";
import { SelectField } from "@/shared/components/ui/fields";
import Panel from "@/shared/components/layout/Panel";
import type { JobAgent, SettingsPatch } from "../api/settings";
import DraftTextField from "./DraftTextField";
import { MIN_SCORES, RUN_TIMES, hhmm, withCurrent } from "./options";

interface JobAgentPanelProps {
  jobAgent: JobAgent;
  onChange: (patch: SettingsPatch) => void;
}

export default function JobAgentPanel({
  jobAgent,
  onChange,
}: JobAgentPanelProps) {
  const { t } = useTranslation();
  const save = (change: Partial<JobAgent>) => onChange({ job_agent: change });

  const runAt = hhmm(jobAgent.run_at);
  const runTimes = withCurrent(
    RUN_TIMES.map((time) => ({ value: time, label: time })),
    { value: runAt, label: runAt },
  );
  const minScores = withCurrent(
    MIN_SCORES.map((score) => ({ value: String(score), label: String(score) })),
    { value: String(jobAgent.min_score), label: String(jobAgent.min_score) },
  );

  return (
    <Panel title={t("settings.jobAgent.title")}>
      <DraftTextField
        label={t("settings.jobAgent.query")}
        placeholder={t("settings.jobAgent.queryPlaceholder")}
        maxLength={200}
        value={jobAgent.query}
        onSave={(query) => save({ query })}
      />
      <div className="grid grid-cols-2 gap-3.5">
        <DraftTextField
          label={t("settings.jobAgent.location")}
          placeholder={t("settings.jobAgent.locationPlaceholder")}
          maxLength={200}
          value={jobAgent.location}
          onSave={(location) => save({ location })}
        />
        <SelectField
          label={t("settings.jobAgent.runAt")}
          options={runTimes}
          value={runAt}
          onChange={(event) => save({ run_at: event.target.value })}
        />
      </div>
      <SelectField
        label={t("settings.jobAgent.minScore")}
        options={minScores}
        value={String(jobAgent.min_score)}
        onChange={(event) => save({ min_score: Number(event.target.value) })}
      />
    </Panel>
  );
}
