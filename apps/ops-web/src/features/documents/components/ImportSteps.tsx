import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";

const STEPS = ["read", "check", "look"] as const;

export default function ImportSteps({ read }: { read: boolean }) {
  const { t } = useTranslation();
  const now = read ? 2 : 0;

  return (
    <ol
      aria-label={t("documents.importPage.steps.label")}
      className="m-0 flex list-none flex-wrap gap-x-8 gap-y-3 p-0"
    >
      {STEPS.map((step, index) => (
        <li
          key={step}
          aria-current={index === now ? "step" : undefined}
          className={cn(
            "flex items-center gap-2.5 text-sm/[1.6]",
            index === now ? "text-ink font-semibold" : "text-ink-3 font-medium",
          )}
        >
          <span
            aria-hidden="true"
            className={cn(
              "flex size-[26px] items-center justify-center rounded-full border text-[13px] font-semibold",
              index < now && "bg-ok-bg text-ok border-ok-bg",
              index === now && "bg-primary text-on-primary border-primary",
              index > now && "border-hair",
            )}
          >
            {index < now ? "✓" : index + 1}
          </span>
          {t(`documents.importPage.steps.${step}`)}
        </li>
      ))}
    </ol>
  );
}
