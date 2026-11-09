import { useTranslation } from "react-i18next";
import { CheckboxRow } from "@/shared/components/ui/fields";
import Panel from "@/shared/components/layout/Panel";
import type { Automation, SettingsPatch } from "../../api/settings";

const RULES = [
  "tailor_strong_matches",
  "follow_up_reminders",
  "suggest_replies",
] as const;

interface AutomationPanelProps {
  automation: Automation;
  onChange: (patch: SettingsPatch) => void;
}

export default function AutomationPanel({
  automation,
  onChange,
}: AutomationPanelProps) {
  const { t } = useTranslation();

  return (
    <Panel title={t("settings.automation.title")} className="gap-3.5">
      {RULES.map((rule) => (
        <CheckboxRow
          key={rule}
          label={t(`settings.automation.rules.${rule}.label`)}
          note={t(`settings.automation.rules.${rule}.note`)}
          checked={automation[rule]}
          onChange={(event) =>
            onChange({ automation: { [rule]: event.target.checked } })
          }
        />
      ))}
      <CheckboxRow
        label={t("settings.automation.approval.label")}
        note={t("settings.automation.approval.note")}
        checked
        disabled
        readOnly
      />
    </Panel>
  );
}
