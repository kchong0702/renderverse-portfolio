import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { Job } from "@/features/jobs";
import { buttonClass } from "@/shared/components/button";
import { SelectField, TextField } from "@/shared/components/fields";
import { cn } from "@/shared/lib/cn";
import type { ApplicationCreate, ApplicationUpdate } from "../api/applications";
import { STAGES } from "../lib/stages";

interface ApplicationFormProps {
  application: ApplicationUpdate & { by_hand: boolean };
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
    job_id: "",
    company: application.company,
    role: application.role,
    url: "",
    location: "",
    stage: application.stage,
    applied_on: application.applied_on ?? "",
  });
  const set = (change: Partial<typeof draft>) =>
    setDraft((current) => ({ ...current, ...change }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const write = { stage: draft.stage, applied_on: draft.applied_on || null };
    onSubmit(
      draft.job_id
        ? { ...write, job_id: draft.job_id }
        : {
            ...write,
            company: draft.company.trim(),
            role: draft.role.trim(),
            url: draft.url.trim(),
            location: draft.location.trim(),
          },
    );
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
          onChange={(event) => set({ job_id: event.target.value })}
        />
      )}
      {!draft.job_id && application.by_hand && (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-3.5">
          <TextField
            label={t("applications.form.company")}
            autoFocus
            required={jobs !== null}
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
          {jobs && (
            <>
              <TextField
                type="url"
                label={t("applications.form.url")}
                maxLength={2000}
                value={draft.url}
                onChange={(event) => set({ url: event.target.value })}
              />
              <TextField
                label={t("applications.form.location")}
                maxLength={200}
                value={draft.location}
                onChange={(event) => set({ location: event.target.value })}
              />
            </>
          )}
        </div>
      )}
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
            className={cn(buttonClass("danger"), "ml-auto")}
          >
            {t("applications.form.delete")}
          </button>
        )}
      </div>
    </form>
  );
}
