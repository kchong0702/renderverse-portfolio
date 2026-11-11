import {
  entryFields,
  type Date as DocumentDate,
  type Value,
} from "@renderverse/document-renderer";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import type { DocumentRecord, Edit } from "../api/documents";
import { entryAt, partsOf, valueOf } from "../lib/items";
import { sourceName } from "../lib/sources";
import { useEditorStore } from "../state/editorStore";

function LiveField({
  label,
  value,
  placeholder,
  onChange,
  className,
}: {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (text: string) => void;
  className?: string;
}) {
  const [draft, setDraft] = useState(value);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) setDraft(value);
  }, [focused, value]);

  return (
    <label className={`flex flex-col gap-1.5 ${className ?? ""}`}>
      <span className="text-ink-3 text-[13px]">{label}</span>
      <input
        type="text"
        value={draft}
        placeholder={placeholder}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onChange={(event) => {
          setDraft(event.target.value);
          onChange(event.target.value);
        }}
        className="border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 text-sm"
      />
    </label>
  );
}

export default function EntryPanel({
  document,
  path,
  source,
  onEdit,
}: {
  document: DocumentRecord;
  path: string;
  source: string;
  onEdit: (edits: Edit[]) => void;
}) {
  const { t } = useTranslation();
  const closeDetails = useEditorStore((state) => state.closeDetails);
  const found = entryAt(document.body.content.blocks, path)!;
  const fields = entryFields[found.block.kind];
  const { title, subtitle, dates, place } = partsOf(
    found.item!,
    found.block.kind,
  );
  const labels: Record<string, string> = t("documents.entryPanel.fields", {
    returnObjects: true,
  });
  const origin = title.src?.[0];
  const update = (field: string, value: Value | DocumentDate | null) =>
    onEdit([{ kind: "update_field", path: `${path}/${field}`, value }]);

  return (
    <div className="flex flex-col gap-3.5 p-5">
      <div className="flex flex-col gap-0.5">
        <h2 className="m-0 text-[15px] font-semibold">
          {t(
            found.block.kind === "education"
              ? "documents.entryPanel.education"
              : "documents.entryPanel.experience",
          )}
        </h2>
        <span className="text-ink-3 text-[13px]">
          {t("documents.entryPanel.hint")}
        </span>
      </div>
      <LiveField
        label={labels[fields.title]}
        value={title.text}
        onChange={(text) => update(fields.title, valueOf(text, source))}
      />
      <LiveField
        label={labels[fields.subtitle]}
        value={subtitle?.text ?? ""}
        onChange={(text) => update(fields.subtitle, valueOf(text, source))}
      />
      <div className="flex flex-wrap gap-3">
        <LiveField
          label={t("documents.entryPanel.fields.dates")}
          value={dates?.text.text ?? ""}
          onChange={(text) =>
            update(fields.dates, { ...dates, text: valueOf(text, source) })
          }
          className="flex-[1_1_140px]"
        />
        {fields.place && (
          <LiveField
            label={t("documents.entryPanel.fields.location")}
            value={place?.text ?? ""}
            placeholder={t("documents.entryPanel.locationPlaceholder")}
            onChange={(text) =>
              update(fields.place!, text ? valueOf(text, source) : null)
            }
            className="flex-[1_1_140px]"
          />
        )}
      </div>
      {origin && (
        <span className="text-ink-3 text-[13px]">
          {t("documents.entryPanel.source", {
            source: sourceName(t, origin, document.lines),
          })}
        </span>
      )}
      <button
        type="button"
        onClick={closeDetails}
        className={`${buttonClass("primary")} self-start`}
      >
        {t("documents.entryPanel.done")}
      </button>
    </div>
  );
}
