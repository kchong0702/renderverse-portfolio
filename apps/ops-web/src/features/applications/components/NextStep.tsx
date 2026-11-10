import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { dayMonth, relativeDay } from "@/shared/lib/dates";
import type { Application } from "../api/applications";
import { followUpDays, isDue } from "../lib/stages";

export default function NextStep({
  application,
  className,
}: {
  application: Application;
  className?: string;
}) {
  const { t, i18n } = useTranslation();
  const { stage, next_step, next_step_at, next_step_due, applied_on } =
    application;
  const followUp = followUpDays(application);
  const text =
    stage === "offer" && next_step_due
      ? t("applications.decideBy", {
          when: dayMonth(new Date(`${next_step_due}T00:00`), i18n.language),
        })
      : next_step_at
        ? [
            new Intl.DateTimeFormat(i18n.language, {
              weekday: "short",
              hour: "2-digit",
              minute: "2-digit",
              hourCycle: "h23",
            }).format(new Date(next_step_at)),
            next_step,
          ]
            .filter(Boolean)
            .join(" · ")
        : next_step ||
          (followUp !== null
            ? t("applications.followUp", { count: followUp })
            : applied_on &&
              t("applications.applied", {
                when: relativeDay(applied_on, i18n.language),
              }));

  return text ? (
    <span
      className={cn(
        isDue(application) ? "text-warn font-bold" : "text-ink-3 font-medium",
        className,
      )}
    >
      {text}
    </span>
  ) : null;
}
