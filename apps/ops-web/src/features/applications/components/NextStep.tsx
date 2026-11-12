import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { dayMonth, relativeDay } from "@/shared/lib/dates";
import type { Application } from "../api/applications";
import { followUpDays, isDue, stepTitle } from "../lib/stages";

export default function NextStep({
  application,
  className,
}: {
  application: Application;
  className?: string;
}) {
  const { t, i18n } = useTranslation();
  const { next_step, overdue, applied_on } = application;
  const followUp = followUpDays(application);
  const text =
    overdue.length > 0
      ? t("applications.overdue", { title: stepTitle(overdue[0], t) })
      : next_step?.kind === "offer_deadline" && next_step.due_on
        ? t("applications.decideBy", {
            when: dayMonth(
              new Date(`${next_step.due_on}T00:00`),
              i18n.language,
            ),
          })
        : next_step?.starts_at
          ? [
              new Intl.DateTimeFormat(i18n.language, {
                weekday: "short",
                hour: "2-digit",
                minute: "2-digit",
                hourCycle: "h23",
              }).format(new Date(next_step.starts_at)),
              stepTitle(next_step, t),
            ].join(" · ")
          : next_step?.due_on
            ? t("applications.dueOn", {
                title: stepTitle(next_step, t),
                when: dayMonth(
                  new Date(`${next_step.due_on}T00:00`),
                  i18n.language,
                ),
              })
            : followUp !== null
              ? t("applications.followUp", { count: followUp })
              : applied_on &&
                t("applications.applied", {
                  when: relativeDay(applied_on, i18n.language),
                });

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
