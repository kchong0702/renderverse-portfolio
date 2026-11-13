import { useTranslation } from "react-i18next";
import type { Preferences, PreferencesPatch } from "@/features/preferences";
import { SelectField } from "@/shared/components/fields";
import Panel from "@/shared/components/Panel";
import { MIN_SCORES, RUN_TIMES, hhmm, withCurrent } from "../lib/options";
import DraftTextField from "@/shared/components/DraftTextField";

interface JobAgentPanelProps {
  preferences: Preferences;
  onChange: (patch: PreferencesPatch) => void;
}

export default function JobAgentPanel({
  preferences,
  onChange,
}: JobAgentPanelProps) {
  const { t } = useTranslation();

  const runAt = hhmm(preferences.run_at);
  const runTimes = withCurrent(
    RUN_TIMES.map((time) => ({ value: time, label: time })),
    { value: runAt, label: runAt },
  );
  const minScores = withCurrent(
    MIN_SCORES.map((score) => ({ value: String(score), label: String(score) })),
    {
      value: String(preferences.min_score),
      label: String(preferences.min_score),
    },
  );

  return (
    <Panel title={t("settings.jobAgent.title")}>
      <DraftTextField
        label={t("settings.jobAgent.query")}
        placeholder={t("settings.jobAgent.queryPlaceholder")}
        maxLength={200}
        value={preferences.target_roles}
        onSave={(target_roles) => onChange({ target_roles })}
      />
      <div className="grid grid-cols-2 gap-3.5">
        <DraftTextField
          label={t("settings.jobAgent.location")}
          placeholder={t("settings.jobAgent.locationPlaceholder")}
          maxLength={200}
          value={preferences.location}
          onSave={(location) => onChange({ location })}
        />
        <SelectField
          label={t("settings.jobAgent.runAt")}
          options={runTimes}
          value={runAt}
          onChange={(event) => onChange({ run_at: event.target.value })}
        />
      </div>
      <SelectField
        label={t("settings.jobAgent.minScore")}
        options={minScores}
        value={String(preferences.min_score)}
        onChange={(event) =>
          onChange({ min_score: Number(event.target.value) })
        }
      />
    </Panel>
  );
}
