import { useTranslation } from "react-i18next";
import { SelectField } from "@/shared/ui/fields";
import Panel from "@/shared/ui/Panel";
import type { AiProvider, Scheduling, SettingsPatch } from "../api/settings";
import { MEETING_GAPS, WORK_HOURS, hhmm, withCurrent } from "./options";

const PROVIDERS: AiProvider[] = ["claude", "openai", "glm"];

interface SchedulingPanelProps {
  scheduling: Scheduling;
  aiProvider: AiProvider;
  onChange: (patch: SettingsPatch) => void;
}

export default function SchedulingPanel({
  scheduling,
  aiProvider,
  onChange,
}: SchedulingPanelProps) {
  const { t } = useTranslation();

  const hoursLabel = (start: string, end: string) =>
    t("settings.scheduling.hoursRange", { start, end });
  const start = hhmm(scheduling.work_day_start);
  const end = hhmm(scheduling.work_day_end);
  const workHours = withCurrent(
    WORK_HOURS.map(([from, to]) => ({
      value: `${from}-${to}`,
      label: hoursLabel(from, to),
    })),
    { value: `${start}-${end}`, label: hoursLabel(start, end) },
  );
  const gapLabel = (minutes: number) =>
    t("settings.scheduling.gap", { count: minutes });
  const gaps = withCurrent(
    MEETING_GAPS.map((minutes) => ({
      value: String(minutes),
      label: gapLabel(minutes),
    })),
    {
      value: String(scheduling.meeting_gap_minutes),
      label: gapLabel(scheduling.meeting_gap_minutes),
    },
  );

  return (
    <Panel title={t("settings.scheduling.title")}>
      <div className="grid grid-cols-2 gap-3.5">
        <SelectField
          label={t("settings.scheduling.workHours")}
          options={workHours}
          value={`${start}-${end}`}
          onChange={(event) => {
            const [work_day_start, work_day_end] =
              event.target.value.split("-");
            onChange({ scheduling: { work_day_start, work_day_end } });
          }}
        />
        <SelectField
          label={t("settings.scheduling.meetingGap")}
          options={gaps}
          value={String(scheduling.meeting_gap_minutes)}
          onChange={(event) =>
            onChange({
              scheduling: { meeting_gap_minutes: Number(event.target.value) },
            })
          }
        />
      </div>
      <SelectField
        label={t("settings.scheduling.aiModel")}
        options={PROVIDERS.map((provider) => ({
          value: provider,
          label: t(`settings.scheduling.providers.${provider}`),
        }))}
        value={aiProvider}
        onChange={(event) =>
          onChange({ ai_provider: event.target.value as AiProvider })
        }
      />
    </Panel>
  );
}
