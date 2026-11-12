import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { stepTitle, useSaveStep, type Step } from "@/features/applications";
import { buttonClass } from "@/shared/components/button";
import Panel from "@/shared/components/Panel";

interface StepDetailProps {
  step: Step;
  company: string | null;
  onClose: () => void;
}

export default function StepDetail({
  step,
  company,
  onClose,
}: StepDetailProps) {
  const { t, i18n } = useTranslation();
  const save = useSaveStep();
  const title = stepTitle(step, t);
  const close = (status: "done" | "cancelled") =>
    save.mutate({ ...step, status }, { onSuccess: onClose });
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panel.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, []);

  return (
    <div ref={panel}>
      <Panel
        title={company ? t("calendar.task", { step: title, company }) : title}
      >
        <p className="text-ink-3 m-0 text-sm">
          {[
            step.starts_at &&
              new Intl.DateTimeFormat(i18n.language, {
                weekday: "short",
                day: "numeric",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
                hourCycle: "h23",
              }).format(new Date(step.starts_at)),
            step.format && t(`applications.steps.form.formats.${step.format}`),
            step.location,
            step.status !== "open" &&
              t(`applications.steps.statuses.${step.status}`),
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {save.isError && (
          <p role="alert" className="text-crit m-0 text-sm">
            {t("applications.steps.form.failed", {
              reason: save.error.message,
            })}
          </p>
        )}
        <div className="flex gap-2.5">
          {step.status === "open" && (
            <>
              <button
                type="button"
                className={buttonClass("primary")}
                disabled={save.isPending}
                onClick={() => close("done")}
              >
                {t("applications.steps.done")}
              </button>
              <button
                type="button"
                className={buttonClass("muted")}
                disabled={save.isPending}
                onClick={() => close("cancelled")}
              >
                {t("applications.steps.cancel")}
              </button>
            </>
          )}
          <button type="button" className={buttonClass()} onClick={onClose}>
            {t("calendar.close")}
          </button>
        </div>
      </Panel>
    </div>
  );
}
