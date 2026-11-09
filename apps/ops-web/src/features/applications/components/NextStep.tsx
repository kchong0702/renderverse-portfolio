import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { relativeDay } from "@/shared/lib/dates";
import type { Application } from "../api/applications";
import { isDue } from "../lib/stages";

export default function NextStep({
  application,
  className,
}: {
  application: Application;
  className?: string;
}) {
  const { t, i18n } = useTranslation();
  const { next_step, next_step_at, applied_on } = application;
  const when =
    next_step_at &&
    new Intl.DateTimeFormat(i18n.language, {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(new Date(next_step_at));
  const text = next_step
    ? [next_step, when].filter(Boolean).join(" · ")
    : applied_on
      ? t("applications.applied", {
          when: relativeDay(applied_on, i18n.language),
        })
      : when;

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
