import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import App from "@/app/App";
import { queryClient } from "@/app/queryClient";
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
  var lng = (i18n.language || navigator.language || "en").toLowerCase();
  document.documentElement.setAttribute(
    "data-lang",
    lng.startsWith("zh") ? "zh" : "en",
  );
})();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>,
);
