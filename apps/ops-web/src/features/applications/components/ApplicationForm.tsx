import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { Job } from "@/features/jobs";
import { buttonClass } from "@/shared/components/button";
import { SelectField, TextField } from "@/shared/components/fields";
import { cn } from "@/shared/lib/cn";
import { localDateTime } from "@/shared/lib/dates";
import type { ApplicationCreate, NextStepFormat } from "../api/applications";
import { STAGES } from "../lib/stages";

const FORMATS: NextStepFormat[] = ["video", "phone", "on_site"];

interface ApplicationFormProps {
  application: ApplicationCreate;
  jobs: Job[] | null;
  pending: boolean;
  error: string | null;
  onSubmit: (application: ApplicationCreate) => void;
  onCancel: () => void;
  onDelete?: () => void;
}

export default function ApplicationForm({
  application,
  jobs,
  pending,
  error,
  onSubmit,
  onCancel,
  onDelete,
}: ApplicationFormProps) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState({
    ...application,
    job_id: application.job_id ?? "",
    applied_on: application.applied_on ?? "",
    next_step_at: application.next_step_at
      ? localDateTime(new Date(application.next_step_at))
      : "",
    next_step_due: application.next_step_due ?? "",
    next_step_format: application.next_step_format ?? ("" as const),
    next_step_location: application.next_step_location ?? "",
  });
  const set = (change: Partial<typeof draft>) =>
    setDraft((current) => ({ ...current, ...change }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      job_id: draft.job_id || null,
      company: draft.company.trim(),
      role: draft.role.trim(),
      stage: draft.stage,
      applied_on: draft.applied_on || null,
      next_step: draft.next_step.trim(),
      next_step_at: draft.next_step_at
        ? new Date(draft.next_step_at).toISOString()
        : null,
      next_step_due: draft.next_step_due || null,
      next_step_format: draft.next_step_format || null,
      next_step_location: draft.next_step_location.trim() || null,
    });
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3.5">
      {jobs && (
        <SelectField
          label={t("applications.form.job")}
          value={draft.job_id}
          options={[
            { value: "", label: t("applications.form.noJob") },
            ...jobs.map((job) => ({
              value: job.id,
              label: [job.title, job.company].filter(Boolean).join(" · "),
            })),
          ]}
          onChange={(event) => {
            const job = jobs.find((j) => j.id === event.target.value);
            set(
              job
                ? { job_id: job.id, company: job.company, role: job.title }
                : { job_id: "" },
            );
          }}
        />
      )}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-3.5">
        <TextField
          label={t("applications.form.company")}
          autoFocus
          required
          maxLength={200}
          value={draft.company}
          onChange={(event) => set({ company: event.target.value })}
        />
        <TextField
          label={t("applications.form.role")}
          required
          maxLength={200}
          value={draft.role}
          onChange={(event) => set({ role: event.target.value })}
        />
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(180px,100%),1fr))] gap-3.5">
        <SelectField
          label={t("applications.form.stage")}
          value={draft.stage}
          options={STAGES.map((stage) => ({
            value: stage,
            label: t(`applications.stages.${stage}`),
          }))}
          onChange={(event) => {
            const stage = STAGES.find((s) => s === event.target.value);
            if (stage) set({ stage });
          }}
        />
        <TextField
          type="date"
          label={t("applications.form.appliedOn")}
          value={draft.applied_on}
          onChange={(event) => set({ applied_on: event.target.value })}
        />
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-3.5">
        <TextField
          label={t("applications.form.nextStep")}
          placeholder={t("applications.form.nextStepPlaceholder")}
          maxLength={200}
          value={draft.next_step}
          onChange={(event) => set({ next_step: event.target.value })}
        />
        <TextField
          type="datetime-local"
          label={t("applications.form.nextStepAt")}
          value={draft.next_step_at}
          onChange={(event) => set({ next_step_at: event.target.value })}
        />
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(180px,100%),1fr))] gap-3.5">
        <TextField
          type="date"
          label={t("applications.form.dueBy")}
          value={draft.next_step_due}
          onChange={(event) => set({ next_step_due: event.target.value })}
        />
        <SelectField
          label={t("applications.form.format")}
          value={draft.next_step_format}
          options={[
            { value: "", label: t("applications.form.noFormat") },
            ...FORMATS.map((format) => ({
              value: format,
              label: t(`applications.form.formats.${format}`),
            })),
          ]}
          onChange={(event) =>
            set({
              next_step_format:
                FORMATS.find((format) => format === event.target.value) ?? "",
            })
          }
        />
        <TextField
          label={t("applications.form.location")}
          maxLength={200}
          value={draft.next_step_location}
          onChange={(event) => set({ next_step_location: event.target.value })}
        />
      </div>
      {error && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("applications.form.failed", { reason: error })}
        </p>
      )}
      <div className="flex gap-2.5">
        <button
          type="submit"
          disabled={pending}
          className={buttonClass("primary")}
        >
          {pending
            ? t("applications.form.saving")
            : t("applications.form.save")}
        </button>
        <button type="button" onClick={onCancel} className={buttonClass()}>
          {t("applications.form.cancel")}
        </button>
        {onDelete && (
          <button
            type="button"
            onClick={onDelete}
            className={cn(buttonClass(), "text-crit ml-auto")}
          >
            {t("applications.form.delete")}
          </button>
        )}
      </div>
    </form>
  );
}
