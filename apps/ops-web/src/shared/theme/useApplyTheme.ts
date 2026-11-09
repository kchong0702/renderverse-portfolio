import { useEffect, useSyncExternalStore } from "react";
import { useThemeStore } from "./themeStore";

const darkQuery = "(prefers-color-scheme: dark)";

function subscribe(onChange: () => void) {
  const media = window.matchMedia(darkQuery);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

export function useResolvedTheme(): "light" | "dark" {
  const mode = useThemeStore((state) => state.mode);
  const systemDark = useSyncExternalStore(
    subscribe,
    () => window.matchMedia(darkQuery).matches,
  );
  if (mode === "system") return systemDark ? "dark" : "light";
  return mode;
}

export function useApplyTheme() {
  const theme = useResolvedTheme();
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
}
