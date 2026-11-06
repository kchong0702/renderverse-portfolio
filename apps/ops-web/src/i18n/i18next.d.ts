import "i18next";
import type { resources } from "@/i18n";

// Type-checks every t() key against en.json
declare module "i18next" {
  interface CustomTypeOptions {
    resources: (typeof resources)["en"];
  }
}
