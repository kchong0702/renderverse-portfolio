import { useState } from "react";
import { useTranslation } from "react-i18next";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import StateMessage from "@/shared/components/StateMessage";
import { dayMonth } from "@/shared/lib/dates";
import type { Application, Step, StepWrite } from "../api/applications";
import { useAddStep, useSaveStep, useSteps } from "../hooks/useApplications";
import { stepTitle } from "../lib/stages";
import StepForm from "./StepForm";

const NEW_STEP: StepWrite = {
  kind: "interview",
  title: "",
  starts_at: null,
  ends_at: null,
  due_on: null,
  format: null,
  location: null,
  status: "open",
};

export default function StepList({
  application,
}: {
  application: Application;
}) {
  const { t, i18n } = useTranslation();
  const steps = useSteps(application.id);
  const add = useAddStep();
  const save = useSaveStep();
  const [editing, setEditing] = useState<string | null>(null);
  const overdue = new Set(application.overdue.map(({ id }) => id));

  const when = (step: Step) =>
    step.starts_at
      ? new Intl.DateTimeFormat(i18n.language, {
          weekday: "short",
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          hourCycle: "h23",
        }).format(new Date(step.starts_at))
      : step.due_on &&
        t("applications.steps.due", {
          when: dayMonth(new Date(`${step.due_on}T00:00`), i18n.language),
        });

  return (
    <section
      aria-label={t("applications.steps.title")}
      className="flex flex-col gap-3"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-ink m-0 text-[15px] font-semibold">
          {t("applications.steps.title")}
        </h3>
        {editing === null && (
          <button
            type="button"
            className={buttonClass()}
            onClick={() => setEditing("new")}
          >
            {t("applications.steps.add")}
          </button>
        )}
      </div>
      {editing === "new" && (
        <StepForm
          step={NEW_STEP}
          pending={add.isPending}
          error={add.isError ? add.error.message : null}
          onCancel={() => setEditing(null)}
          onSubmit={(step) =>
            add.mutate(
              { applicationId: application.id, step },
              { onSuccess: () => setEditing(null) },
            )
          }
        />
      )}
      {steps.isError ? (
        <StateMessage tone="error">
          {t("applications.steps.loadFailed", { reason: steps.error.message })}
        </StateMessage>
      ) : !steps.data ? (
        <StateMessage>{t("common.loading")}</StateMessage>
      ) : steps.data.length === 0 ? (
        <p className="text-ink-3 m-0 text-sm">
          {t("applications.steps.empty")}
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col p-0">
          {steps.data.map((step) =>
            editing === step.id ? (
              <li key={step.id} className="border-hair-soft border-b py-3">
                <StepForm
                  step={step}
                  kindLocked={step.email_thread_id !== null}
                  pending={save.isPending}
                  error={save.isError ? save.error.message : null}
                  onCancel={() => setEditing(null)}
                  onSubmit={(changed) =>
                    save.mutate(
                      { ...step, ...changed },
                      { onSuccess: () => setEditing(null) },
                    )
                  }
                />
              </li>
            ) : (
              <li
                key={step.id}
                className="border-hair-soft flex flex-wrap items-center gap-3 border-b py-3 last:border-b-0"
              >
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{stepTitle(step, t)}</span>
                    {step.title && (
                      <Badge>
                        {t(`applications.steps.kinds.${step.kind}`)}
                      </Badge>
                    )}
                    {step.id === application.next_step?.id && (
                      <Badge tone="accent">
                        {t("applications.steps.next")}
                      </Badge>
                    )}
                    {overdue.has(step.id) && (
                      <Badge tone="warn">
                        {t("applications.steps.overdue")}
                      </Badge>
                    )}
                    {step.status !== "open" && (
                      <Badge tone={step.status === "done" ? "ok" : "neutral"}>
                        {t(`applications.steps.statuses.${step.status}`)}
                      </Badge>
                    )}
                  </span>
                  <span className="text-ink-3 text-sm">
                    {[
                      when(step),
                      step.format &&
                        t(`applications.steps.form.formats.${step.format}`),
                      step.location,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </span>
                <span className="flex gap-2">
                  <button
                    type="button"
                    aria-label={t("applications.steps.edit", {
                      title: stepTitle(step, t),
                    })}
                    className={buttonClass()}
                    disabled={editing !== null}
                    onClick={() => setEditing(step.id)}
                  >
                    {t("applications.steps.editShort")}
                  </button>
                  {step.status === "open" && (
                    <>
                      <button
                        type="button"
                        className={buttonClass()}
                        disabled={save.isPending}
                        onClick={() => save.mutate({ ...step, status: "done" })}
                      >
                        {t("applications.steps.done")}
                      </button>
                      <button
                        type="button"
                        className={buttonClass("muted")}
                        disabled={save.isPending}
                        onClick={() =>
                          save.mutate({ ...step, status: "cancelled" })
                        }
                      >
                        {t("applications.steps.cancel")}
                      </button>
                    </>
                  )}
                </span>
              </li>
            ),
          )}
        </ul>
      )}
      {save.isError && editing === null && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("applications.steps.form.failed", { reason: save.error.message })}
        </p>
      )}
    </section>
  );
}
