import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "system" | "light" | "dark";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

// The key index.html reads before the first paint, so a dark page never flashes light
export const THEME_STORAGE_KEY = "ops:theme";

export const useThemeStore = create<ThemeState>()(
  persist((set) => ({ mode: "system", setMode: (mode) => set({ mode }) }), {
    name: THEME_STORAGE_KEY,
  }),
);
