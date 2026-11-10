import { useTranslation } from "react-i18next";
import Panel from "@/shared/components/Panel";
import Segmented from "@/shared/components/Segmented";
import { useThemeStore, type ThemeMode } from "@/shared/theme/themeStore";

export default function AppearancePanel() {
  const { t } = useTranslation();
  const { mode, setMode } = useThemeStore();
  const modes: ThemeMode[] = ["system", "light", "dark"];

  return (
    <Panel title={t("settings.appearance.title")}>
      <Segmented
        label={t("settings.appearance.theme")}
        value={mode}
        options={modes.map((value) => ({
          value,
          label: t(`settings.appearance.modes.${value}`),
        }))}
        onChange={setMode}
      />
    </Panel>
  );
}
