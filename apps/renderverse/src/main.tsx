import React from "react";
import ReactDOM from "react-dom/client";
import App from "@/app/App";
import AppProviders from "@/app/providers";
import "./index.css";

import i18n from "@/i18n";

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
  document.documentElement.setAttribute(
    "data-lang",
    lng.startsWith("zh") ? "zh" : "en",
  );
});

// Set initial data-lang before render
(function () {
  const lng = (i18n.language || navigator.language || "en").toLowerCase();
  document.documentElement.setAttribute(
    "data-lang",
    lng.startsWith("zh") ? "zh" : "en",
  );
})();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </React.StrictMode>,
);
