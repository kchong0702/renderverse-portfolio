import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import { SelectField, TextField } from "@/shared/components/fields";
import { localDateTime } from "@/shared/lib/dates";
import type { NextStepFormat, StepKind, StepWrite } from "../api/applications";

const KINDS: StepKind[] = [
  "interview",
  "follow_up",
  "take_home",
  "offer_deadline",
];
const FORMATS: NextStepFormat[] = ["video", "phone", "on_site"];

interface StepFormProps {
  step: StepWrite;
  kindLocked?: boolean;
  pending: boolean;
  error: string | null;
  onSubmit: (step: StepWrite) => void;
  onCancel: () => void;
}

export default function StepForm({
  step,
  kindLocked = false,
  pending,
  error,
  onSubmit,
  onCancel,
}: StepFormProps) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState({
    ...step,
    starts_at: step.starts_at ? localDateTime(new Date(step.starts_at)) : "",
    ends_at: step.ends_at ? localDateTime(new Date(step.ends_at)) : "",
    due_on: step.due_on ?? "",
    format: step.format ?? ("" as const),
    location: step.location ?? "",
  });
  const set = (change: Partial<typeof draft>) =>
    setDraft((current) => ({ ...current, ...change }));
  const timeless = !draft.starts_at && !draft.due_on;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      ...draft,
      title: draft.title.trim(),
      starts_at: draft.starts_at
        ? new Date(draft.starts_at).toISOString()
        : null,
      ends_at: draft.ends_at ? new Date(draft.ends_at).toISOString() : null,
      due_on: draft.due_on || null,
      format: draft.format || null,
      location: draft.location.trim() || null,
    });
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3.5">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-3.5">
        <SelectField
          label={t("applications.steps.form.kind")}
          disabled={kindLocked}
          value={draft.kind}
          options={KINDS.map((kind) => ({
            value: kind,
            label: t(`applications.steps.kinds.${kind}`),
          }))}
          onChange={(event) => {
            const kind = KINDS.find((k) => k === event.target.value);
            if (kind) set({ kind });
          }}
        />
        <TextField
          label={t("applications.steps.form.title")}
          placeholder={t(`applications.steps.kinds.${draft.kind}`)}
          autoFocus
          maxLength={200}
          value={draft.title}
          onChange={(event) => set({ title: event.target.value })}
        />
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-3.5">
        <TextField
          type="datetime-local"
          label={t("applications.steps.form.startsAt")}
          value={draft.starts_at}
          onChange={(event) => set({ starts_at: event.target.value })}
        />
        <TextField
          type="datetime-local"
          label={t("applications.steps.form.endsAt")}
          min={draft.starts_at || undefined}
          value={draft.ends_at}
          onChange={(event) => set({ ends_at: event.target.value })}
        />
        <TextField
          type="date"
          label={t("applications.steps.form.dueOn")}
          value={draft.due_on}
          onChange={(event) => set({ due_on: event.target.value })}
        />
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-3.5">
        <SelectField
          label={t("applications.steps.form.format")}
          value={draft.format}
          options={[
            { value: "", label: t("applications.steps.form.noFormat") },
            ...FORMATS.map((format) => ({
              value: format,
              label: t(`applications.steps.form.formats.${format}`),
            })),
          ]}
          onChange={(event) =>
            set({
              format:
                FORMATS.find((format) => format === event.target.value) ?? "",
            })
          }
        />
        <TextField
          label={t("applications.steps.form.location")}
          maxLength={500}
          value={draft.location}
          onChange={(event) => set({ location: event.target.value })}
        />
      </div>
      {timeless && (
        <p className="text-ink-3 m-0 text-sm">
          {t("applications.steps.form.needsTime")}
        </p>
      )}
      {error && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("applications.steps.form.failed", { reason: error })}
        </p>
      )}
      <div className="flex gap-2.5">
        <button
          type="submit"
          disabled={pending || timeless}
          className={buttonClass("primary")}
        >
          {pending
            ? t("applications.steps.form.saving")
            : t("applications.steps.form.save")}
        </button>
        <button type="button" onClick={onCancel} className={buttonClass()}>
          {t("applications.steps.form.cancel")}
        </button>
      </div>
    </form>
  );
}
