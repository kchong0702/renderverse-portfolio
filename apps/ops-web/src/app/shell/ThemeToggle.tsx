import { useTranslation } from "react-i18next";
import { useThemeStore } from "@/shared/theme/themeStore";
import { useResolvedTheme } from "@/shared/theme/useApplyTheme";
import { MoonIcon, SunIcon } from "@/shared/ui/icons";

export default function ThemeToggle() {
  const { t } = useTranslation();
  const theme = useResolvedTheme();
  const setMode = useThemeStore((state) => state.setMode);
  const next = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={() => setMode(next)}
      aria-label={t(
        next === "dark" ? "shell.useDarkTheme" : "shell.useLightTheme",
      )}
      className="text-side-muted hover:text-side-ink hover:bg-side-tile flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-lg"
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
