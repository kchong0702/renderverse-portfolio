import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import { TextField } from "@/shared/components/fields";
import StateMessage from "@/shared/components/StateMessage";
import {
  useKeepVersion,
  useRestoreVersion,
  useVersions,
} from "../hooks/useDocuments";

export default function VersionsPanel({ documentId }: { documentId: string }) {
  const { t } = useTranslation();
  const versions = useVersions(documentId);
  const keep = useKeepVersion();
  const restore = useRestoreVersion();
  const [label, setLabel] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    keep.mutate(
      { id: documentId, label: label.trim() },
      { onSuccess: () => setLabel("") },
    );
  };

  return (
    <div className="flex flex-col gap-5">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <div className="min-w-[180px] flex-1">
          <TextField
            label={t("documents.versions.label")}
            placeholder={t("documents.versions.labelPlaceholder")}
            maxLength={200}
            value={label}
            onChange={(event) => setLabel(event.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={keep.isPending}
          className={buttonClass("primary")}
        >
          {t("documents.versions.keep")}
        </button>
      </form>
      <p className="text-ink-3 m-0 text-[13px]">
        {t("documents.versions.hint")}
      </p>
      {(keep.isError || restore.isError) && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("documents.versions.failed", {
            reason: (keep.error ?? restore.error)?.message,
          })}
        </p>
      )}
      {versions.isPending ? (
        <StateMessage>{t("common.loading")}</StateMessage>
      ) : versions.isError ? (
        <StateMessage tone="error">
          {t("documents.versions.loadFailed", {
            reason: versions.error.message,
          })}
        </StateMessage>
      ) : (
        <ol className="border-hair m-0 flex list-none flex-col overflow-hidden rounded-xl border p-0">
          {versions.data.map((version) => (
            <li
              key={version.id}
              className="border-hair-soft flex flex-wrap items-center gap-3 border-b px-4 py-3 last:border-b-0"
            >
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-semibold">
                  {t("documents.versions.name", {
                    number: version.number,
                    label: version.label || t("documents.versions.unlabelled"),
                  })}
                </span>
                <span className="text-ink-3 text-xs">
                  {new Date(version.created_at).toLocaleString()}
                </span>
              </span>
              <button
                type="button"
                disabled={restore.isPending}
                onClick={() =>
                  restore.mutate({ id: documentId, versionId: version.id })
                }
                className={buttonClass()}
              >
                {t("documents.versions.restore")}
              </button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
