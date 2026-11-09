import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import type { DocumentImport } from "../api/documents";

const STEPS = ["read", "check", "look"] as const;

export default function ImportSteps({ current }: { current?: DocumentImport }) {
  const { t } = useTranslation();
  const done = current?.status === "done" ? 2 : 0;

  return (
    <ol
      aria-label={t("documents.importPage.steps.label")}
      className="m-0 flex list-none flex-wrap gap-x-8 gap-y-3 p-0"
    >
      {STEPS.map((step, index) => {
        const state =
          index < done ? "done" : index === done && current ? "now" : "later";
        return (
          <li
            key={step}
            aria-current={state === "now" ? "step" : undefined}
            className={cn(
              "flex items-center gap-2.5 text-sm",
              state === "now"
                ? "text-ink font-semibold"
                : "text-ink-3 font-medium",
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "flex size-7 items-center justify-center rounded-full border text-xs",
                state === "done" && "bg-ok-bg text-ok border-ok-bg",
                state === "now" && "bg-primary text-on-primary border-primary",
                state === "later" && "border-hair",
              )}
            >
              {state === "done" ? <Check size={14} /> : index + 1}
            </span>
            {t(`documents.importPage.steps.${step}`)}
          </li>
        );
      })}
    </ol>
  );
}
