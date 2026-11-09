import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import translationEN from "@/i18n/locales/en.json";

export const resources = {
  en: { translation: translationEN },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  debug: false,
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
