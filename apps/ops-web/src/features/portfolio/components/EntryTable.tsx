import { Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import Badge from "@/shared/components/Badge";
import type { Entry, EntryKind, EntryWrite } from "../api/profile";
import { useAddEntry, useDeleteEntry, useSaveEntry } from "../hooks/useProfile";
import EntryForm from "./EntryForm";
import Switch from "./Switch";

const BLANK: EntryWrite = {
  title: "",
  organisation: "",
  location: "",
  start: null,
  end: null,
  summary: "",
  highlights: [],
  archived: false,
};

const columns =
  "grid grid-cols-[minmax(0,1fr)_64px_40px] items-center gap-3 sm:grid-cols-[minmax(0,1fr)_120px_40px] sm:gap-4";

interface EntryRowProps {
  entry: Entry;
  deleteError: string | null;
  onEdit: () => void;
  onDelete: () => void;
}

function EntryRow({ entry, deleteError, onEdit, onDelete }: EntryRowProps) {
  const { t } = useTranslation();
  const toggle = useSaveEntry();
  const from = entry.start?.slice(0, 4);
  const to =
    entry.end === "present"
      ? t("portfolio.period.now")
      : entry.end?.slice(0, 4);

  return (
    <div
      role="row"
      className={`${columns} border-hair-soft border-b px-5 py-4 ${entry.archived ? "opacity-70" : ""}`}
    >
      <span role="cell" className="flex min-w-0 flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            aria-label={t("portfolio.table.edit", { name: entry.title })}
            onClick={onEdit}
            className="text-ink cursor-pointer text-left font-semibold hover:underline"
          >
            {entry.title}
          </button>
          <span className="text-ink-3 text-[13px]">
            {from && to && from !== to
              ? t("portfolio.period.range", { from, to })
              : (from ?? to ?? "")}
          </span>
          {entry.archived && <Badge>{t("portfolio.table.archived")}</Badge>}
        </span>
        <span className="text-ink-2 text-sm">
          {[entry.organisation, entry.summary].filter(Boolean).join(" · ")}
        </span>
        {toggle.isError && (
          <span role="alert" className="text-crit text-sm">
            {t("portfolio.table.toggleFailed", {
              reason: toggle.error.message,
            })}
          </span>
        )}
        {deleteError && (
          <span role="alert" className="text-crit text-sm">
            {t("portfolio.table.deleteFailed", { reason: deleteError })}
          </span>
        )}
      </span>
      <span role="cell" className="flex justify-center">
        <Switch
          label={t("portfolio.table.useInAgent", { name: entry.title })}
          checked={!entry.archived}
          onChange={(on) => toggle.mutate({ ...entry, archived: !on })}
        />
      </span>
      <span role="cell" className="flex justify-end">
        <button
          type="button"
          aria-label={t("portfolio.table.delete", { name: entry.title })}
          onClick={() => {
            if (
              window.confirm(
                t("portfolio.table.confirmDelete", { name: entry.title }),
              )
            )
              onDelete();
          }}
          className="text-ink-3 hover:text-crit inline-flex size-10 cursor-pointer items-center justify-center rounded-lg"
        >
          <Trash2 size={18} />
        </button>
      </span>
    </div>
  );
}

interface EntryTableProps {
  kind: EntryKind;
  entries: Entry[];
}

export default function EntryTable({ kind, entries }: EntryTableProps) {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const add = useAddEntry();
  const save = useSaveEntry();
  const remove = useDeleteEntry();
  const editing = params.get("edit");
  const adding = editing === `new-${kind}`;

  const setEditing = (id: string | null) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (id) next.set("edit", id);
        else next.delete("edit");
        return next;
      },
      { replace: true },
    );

  return (
    <div className="bg-panel border-hair shadow-card overflow-hidden rounded-xl border">
      <div role="table" aria-labelledby={`${kind}-heading`}>
        <div
          role="row"
          className={`${columns} border-hair text-ink-3 border-b px-5 py-3 text-[13px] font-semibold`}
        >
          <span role="columnheader">{t(`portfolio.kinds.${kind}.column`)}</span>
          <span role="columnheader" className="text-center">
            {t("portfolio.table.agentContext")}
          </span>
          <span role="columnheader" className="sr-only">
            {t("portfolio.table.deleteColumn")}
          </span>
        </div>
        {entries.map((entry) =>
          editing === entry.id ? (
            <div
              key={entry.id}
              role="row"
              className="border-hair-soft border-b px-5 py-4"
            >
              <div role="cell">
                <EntryForm
                  kind={kind}
                  entry={entry}
                  pending={save.isPending}
                  error={save.isError ? save.error.message : null}
                  onCancel={() => setEditing(null)}
                  onSubmit={(write) =>
                    save.mutate(
                      { ...entry, ...write },
                      { onSuccess: () => setEditing(null) },
                    )
                  }
                />
              </div>
            </div>
          ) : (
            <EntryRow
              key={entry.id}
              entry={entry}
              deleteError={
                remove.isError && remove.variables === entry.id
                  ? remove.error.message
                  : null
              }
              onEdit={() => setEditing(entry.id)}
              onDelete={() => remove.mutate(entry.id)}
            />
          ),
        )}
      </div>
      {entries.length === 0 && !adding && (
        <p className="text-ink-3 border-hair-soft m-0 border-b px-5 py-4 text-sm">
          {t(`portfolio.kinds.${kind}.empty`)}
        </p>
      )}
      <div className="px-5 py-3.5">
        {adding ? (
          <EntryForm
            kind={kind}
            entry={BLANK}
            pending={add.isPending}
            error={add.isError ? add.error.message : null}
            onCancel={() => setEditing(null)}
            onSubmit={(write) =>
              add.mutate(
                { ...write, kind },
                { onSuccess: () => setEditing(null) },
              )
            }
          />
        ) : (
          <button
            type="button"
            onClick={() => setEditing(`new-${kind}`)}
            className="text-amber min-h-9 cursor-pointer font-semibold"
          >
            {t(`portfolio.kinds.${kind}.add`)}
          </button>
        )}
      </div>
    </div>
  );
}
