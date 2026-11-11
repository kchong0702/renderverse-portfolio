import { useTranslation } from "react-i18next";
import i18n from "@/i18n";
import { SelectField } from "@/shared/components/fields";
import Panel from "@/shared/components/Panel";
import Segmented from "@/shared/components/Segmented";
import { useThemeStore, type ThemeMode } from "@/shared/theme/themeStore";
import type { ModelChoice, ModelFamily, SettingsPatch } from "../api/settings";
import { useModels } from "../hooks/useSettings";
import { withCurrent } from "../lib/options";

interface SystemPanelProps {
  aiModel: ModelChoice | null;
  onChange: (patch: SettingsPatch) => void;
}

const option = ({ family, model }: ModelChoice) => ({
  value: `${family}:${model}`,
  label: i18n.t("settings.ai.modelOption", {
    family: i18n.t(`settings.ai.providers.${family}`),
    model,
  }),
});

export default function SystemPanel({ aiModel, onChange }: SystemPanelProps) {
  const { t } = useTranslation();
  const models = useModels();
  const { mode, setMode } = useThemeStore();
  const modes: ThemeMode[] = ["system", "light", "dark"];

  const offered = (models.data?.families ?? []).flatMap(({ family, models }) =>
    models.map((model) => option({ family, model })),
  );
  const options = aiModel
    ? withCurrent(offered, option(aiModel))
    : [{ value: "", label: t("settings.ai.harnessDefault") }, ...offered];

  return (
    <Panel title={t("settings.system.title")}>
      <SelectField
        label={t("settings.ai.model")}
        options={options}
        value={aiModel ? option(aiModel).value : ""}
        disabled={!models.isSuccess}
        onChange={(event) => {
          const value = event.target.value;
          const split = value.indexOf(":");
          if (split > 0)
            onChange({
              ai_model: {
                family: value.slice(0, split) as ModelFamily,
                model: value.slice(split + 1),
              },
            });
        }}
      />
      {models.isPending && (
        <p role="status" className="text-ink-3 m-0 text-sm">
          {t("settings.ai.modelsLoading")}
        </p>
      )}
      {models.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("settings.ai.modelsFailed", { reason: models.error.message })}
        </p>
      )}
      <div className="text-ink-3 flex flex-col items-start gap-1.5 text-sm">
        {t("settings.appearance.theme")}
        <Segmented
          label={t("settings.appearance.theme")}
          value={mode}
          options={modes.map((value) => ({
            value,
            label: t(`settings.appearance.modes.${value}`),
          }))}
          onChange={setMode}
        />
      </div>
    </Panel>
  );
}
