import i18next from "i18next";
import en from "./en.json";
import ms from "./ms.json";

const i18n = i18next.createInstance();
i18n.init({
  resources: { en: { translation: en }, ms: { translation: ms } },
  fallbackLng: "en",
  initAsync: false,
  interpolation: { escapeValue: false },
});

export const translator = (language = "en") => i18n.getFixedT(language);
