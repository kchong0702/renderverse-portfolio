import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import {
  CheckboxRow,
  TextAreaField,
  TextField,
} from "@/shared/components/fields";
import type { EntryKind, EntryWrite, YearMonth } from "../api/profile";

interface EntryFormProps {
  kind: EntryKind;
  entry: EntryWrite;
  pending: boolean;
  error: string | null;
  onSubmit: (entry: EntryWrite) => void;
  onCancel: () => void;
}

export default function EntryForm({
  kind,
  entry,
  pending,
  error,
  onSubmit,
  onCancel,
}: EntryFormProps) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState({
    ...entry,
    start: entry.start ?? "",
    end: entry.end === "present" ? "" : (entry.end ?? ""),
    ongoing: entry.end === "present",
    highlights: entry.highlights.join("\n"),
    link: entry.link ?? "",
    code_link: entry.code_link ?? "",
    tools: entry.tools.join(", "),
  });
  const set = (change: Partial<typeof draft>) =>
    setDraft((current) => ({ ...current, ...change }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      title: draft.title.trim(),
      organisation: draft.organisation.trim(),
      location: draft.location.trim(),
      start: (draft.start || null) as YearMonth | null,
      end: draft.ongoing
        ? "present"
        : ((draft.end || null) as YearMonth | null),
      summary: draft.summary.trim(),
      highlights: draft.highlights
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
      link: draft.link.trim() || null,
      code_link: draft.code_link.trim() || null,
      tools: draft.tools
        .split(",")
        .map((tool) => tool.trim())
        .filter(Boolean),
      archived: draft.archived,
      on_site: draft.on_site,
    });
  };

  const month = {
    type: "month",
    placeholder: t("portfolio.form.monthPlaceholder"),
    pattern: "\\d{4}-\\d{2}",
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3.5">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-3.5">
        <TextField
          label={t(`portfolio.kinds.${kind}.title`)}
          autoFocus
          required
          maxLength={200}
          value={draft.title}
          onChange={(event) => set({ title: event.target.value })}
        />
        <TextField
          label={t(`portfolio.kinds.${kind}.organisation`)}
          maxLength={200}
          value={draft.organisation}
          onChange={(event) => set({ organisation: event.target.value })}
        />
        {kind !== "project" && (
          <TextField
            label={t("portfolio.form.location")}
            maxLength={200}
            value={draft.location}
            onChange={(event) => set({ location: event.target.value })}
          />
        )}
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(180px,100%),1fr))] items-end gap-3.5">
        <TextField
          {...month}
          label={t("portfolio.form.start")}
          required={kind === "role"}
          value={draft.start}
          onChange={(event) => set({ start: event.target.value })}
        />
        <TextField
          {...month}
          label={t("portfolio.form.end")}
          disabled={draft.ongoing}
          value={draft.ongoing ? "" : draft.end}
          onChange={(event) => set({ end: event.target.value })}
        />
        <div className="min-h-10 content-center">
          <CheckboxRow
            label={t("portfolio.form.ongoing")}
            checked={draft.ongoing}
            onChange={(event) => set({ ongoing: event.target.checked })}
          />
        </div>
      </div>
      <TextField
        label={t(`portfolio.kinds.${kind}.summary`)}
        value={draft.summary}
        onChange={(event) => set({ summary: event.target.value })}
      />
      <TextAreaField
        label={t("portfolio.form.highlights")}
        placeholder={t("portfolio.form.highlightsPlaceholder")}
        value={draft.highlights}
        onChange={(event) => set({ highlights: event.target.value })}
      />
      {kind === "project" && (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-3.5">
          <TextField
            label={t("portfolio.form.link")}
            type="url"
            maxLength={500}
            placeholder="https://"
            value={draft.link}
            onChange={(event) => set({ link: event.target.value })}
          />
          <TextField
            label={t("portfolio.form.codeLink")}
            type="url"
            maxLength={500}
            placeholder="https://"
            value={draft.code_link}
            onChange={(event) => set({ code_link: event.target.value })}
          />
          <TextField
            label={t("portfolio.form.tools")}
            placeholder={t("portfolio.form.toolsPlaceholder")}
            value={draft.tools}
            onChange={(event) => set({ tools: event.target.value })}
          />
        </div>
      )}
      {error && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("portfolio.form.failed", { reason: error })}
        </p>
      )}
      <div className="flex gap-2.5">
        <button
          type="submit"
          disabled={pending}
          className={buttonClass("primary")}
        >
          {pending ? t("portfolio.form.saving") : t("portfolio.form.save")}
        </button>
        <button type="button" onClick={onCancel} className={buttonClass()}>
          {t("portfolio.form.cancel")}
        </button>
      </div>
    </form>
  );
}
