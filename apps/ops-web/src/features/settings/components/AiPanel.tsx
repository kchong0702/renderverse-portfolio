import { useTranslation } from "react-i18next";
import { SelectField } from "@/shared/components/fields";
import Panel from "@/shared/components/Panel";
import type { ModelChoice, ModelFamily, SettingsPatch } from "../api/settings";
import { useModels } from "../hooks/useSettings";
import { withCurrent } from "../lib/options";

interface AiPanelProps {
  aiModel: ModelChoice | null;
  onChange: (patch: SettingsPatch) => void;
}

export default function AiPanel({ aiModel, onChange }: AiPanelProps) {
  const { t } = useTranslation();
  const models = useModels();

  const option = ({ family, model }: ModelChoice) => ({
    value: `${family}:${model}`,
    label: t("settings.ai.modelOption", {
      family: t(`settings.ai.providers.${family}`),
      model,
    }),
  });
  const offered = (models.data?.families ?? []).flatMap(({ family, models }) =>
    models.map((model) => option({ family, model })),
  );
  const options = aiModel
    ? withCurrent(offered, option(aiModel))
    : [{ value: "", label: t("settings.ai.harnessDefault") }, ...offered];

  return (
    <Panel title={t("settings.ai.title")}>
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
    </Panel>
  );
}
