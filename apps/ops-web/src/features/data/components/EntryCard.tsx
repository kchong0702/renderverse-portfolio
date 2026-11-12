import { Pencil } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  EntryForm,
  Switch,
  useAddEntry,
  useDeleteEntry,
  useSaveEntry,
  type Entry,
  type EntryKind,
  type EntryWrite,
} from "@/features/portfolio";
import Badge from "@/shared/components/Badge";
import { cn } from "@/shared/lib/cn";
import { period } from "../lib/facts";
import Section from "./Section";

const BLANK: EntryWrite = {
  title: "",
  organisation: "",
  location: "",
  start: null,
  end: null,
  summary: "",
  highlights: [],
  link: null,
  code_link: null,
  tools: [],
  archived: false,
  on_site: false,
};

const columns =
  "grid grid-cols-[minmax(0,1fr)_72px_40px] gap-3 px-4 sm:grid-cols-[minmax(0,1fr)_112px_40px] sm:px-[22px]";

function EntryRow({ entry, onEdit }: { entry: Entry; onEdit: () => void }) {
  const { t } = useTranslation();
  const toggle = useSaveEntry();
  const meta = [
    entry.kind === "project" ? entry.summary : entry.organisation,
    entry.kind === "role" ? entry.location : "",
    period(entry.start, entry.end),
  ].filter(Boolean);

  return (
    <div
      role="row"
      className={cn(columns, "border-hair items-center border-t py-3.5")}
    >
      <span role="cell" className="flex min-w-0 flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "font-semibold",
              entry.archived ? "text-ink-3" : "text-ink",
            )}
          >
            {entry.title}
          </span>
          {entry.archived && <Badge>{t("data.entries.off")}</Badge>}
        </span>
        <span className="text-ink-3 text-sm">{meta.join(" · ")}</span>
        {toggle.isError && (
          <span role="alert" className="text-crit text-sm">
            {t("data.notSaved", { reason: toggle.error.message })}
          </span>
        )}
      </span>
      <span role="cell" className="flex justify-center">
        <Switch
          label={t("data.entries.use", { name: entry.title })}
          checked={!entry.archived}
          onChange={(on) => toggle.mutate({ ...entry, archived: !on })}
        />
      </span>
      <span role="cell">
        <button
          type="button"
          aria-label={t("data.entries.edit", { name: entry.title })}
          onClick={onEdit}
          className="text-ink-3 hover:text-ink inline-flex size-10 cursor-pointer items-center justify-center rounded-lg"
        >
          <Pencil size={15} />
        </button>
      </span>
    </div>
  );
}

interface EntryCardProps {
  kind: EntryKind;
  entries: Entry[];
}

export default function EntryCard({ kind, entries }: EntryCardProps) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState<string | null>(null);
  const add = useAddEntry();
  const save = useSaveEntry();
  const remove = useDeleteEntry();
  const off = entries.filter((entry) => entry.archived).length;

  return (
    <Section
      title={t(`data.entries.${kind}.title`)}
      hint={t(`data.entries.${kind}.hint`)}
      summary={[
        t(`data.entries.${kind}.count`, { count: entries.length }),
        off ? t("data.entries.offCount", { count: off }) : "",
      ]
        .filter(Boolean)
        .join(" · ")}
    >
      <div role="table" aria-label={t(`data.entries.${kind}.title`)}>
        <div
          role="row"
          className={cn(columns, "text-ink-3 py-2.5 text-xs font-semibold")}
        >
          <span role="columnheader">{t(`data.entries.${kind}.column`)}</span>
          <span role="columnheader" className="text-center">
            {t("data.entries.uses")}
          </span>
          <span role="columnheader" className="sr-only">
            {t("data.edit")}
          </span>
        </div>
        {entries.map((entry) =>
          editing === entry.id ? (
            <div
              key={entry.id}
              role="row"
              className="border-hair border-t px-4 py-4 sm:px-[22px]"
            >
              <div role="cell">
                <EntryForm
                  kind={kind}
                  entry={entry}
                  pending={save.isPending}
                  error={
                    save.isError
                      ? save.error.message
                      : remove.isError
                        ? remove.error.message
                        : null
                  }
                  onCancel={() => setEditing(null)}
                  onSubmit={(write) =>
                    save.mutate(
                      { ...entry, ...write },
                      { onSuccess: () => setEditing(null) },
                    )
                  }
                  onDelete={() =>
                    remove.mutate(entry.id, {
                      onSuccess: () => setEditing(null),
                    })
                  }
                />
              </div>
            </div>
          ) : (
            <EntryRow
              key={entry.id}
              entry={entry}
              onEdit={() => setEditing(entry.id)}
            />
          ),
        )}
      </div>
      {entries.length === 0 && editing !== "new" && (
        <p className="text-ink-3 border-hair m-0 border-t px-4 py-3.5 text-sm sm:px-[22px]">
          {t(`data.entries.${kind}.empty`)}
        </p>
      )}
      {editing === "new" ? (
        <div className="border-hair border-t px-4 py-4 sm:px-[22px]">
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
        </div>
      ) : (
        <div className="border-hair flex justify-end border-t px-4 py-2 sm:px-[22px]">
          <button
            type="button"
            onClick={() => setEditing("new")}
            className="text-amber min-h-9 cursor-pointer text-sm font-semibold"
          >
            {t(`data.entries.${kind}.add`)}
          </button>
        </div>
      )}
    </Section>
  );
}
