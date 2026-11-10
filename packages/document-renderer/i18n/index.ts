import i18next from "i18next";
import en from "./en.json";
import ms from "./ms.json";
import type { Translate } from "../src/types";

const i18n = i18next.createInstance();
i18n.init({
  resources: { en: { translation: en }, ms: { translation: ms } },
  fallbackLng: "en",
  initAsync: false,
  interpolation: { escapeValue: false },
});

export const translator =
  (language = "en"): Translate =>
  (key) =>
    i18n.t(key, { lng: language, defaultValue: key });
