import * as RadixTabs from "@radix-ui/react-tabs";
import { useIsMutating } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useMe } from "@/features/auth";
import { buttonClass } from "@/shared/components/button";
import StateMessage from "@/shared/components/StateMessage";
import { relativeDay } from "@/shared/lib/dates";
import { cn } from "@/shared/lib/cn";
import {
  useDeleteDocument,
  useDesignDocument,
  useDocument,
  useExportPdf,
  usePendingChangeset,
  useSave,
  useSaves,
  useSetMaster,
} from "../hooks/useDocuments";
import { pathOf } from "../lib/changes";
import { entryAt } from "../lib/items";
import { editDocumentMutationOptions } from "../queries/documents";
import { useEditorStore, type Panel } from "../state/editorStore";
import AssistantPanel from "./AssistantPanel";
import DesignPanel from "./DesignPanel";
import DocumentPage from "./DocumentPage";
import EntryPanel from "./EntryPanel";

const tabClass =
  "text-ink-3 data-[state=active]:text-ink min-h-[46px] cursor-pointer border-0 bg-transparent px-3 text-sm font-medium data-[state=active]:font-semibold data-[state=active]:shadow-[inset_0_-2px_0_var(--color-amber)]";

const downloadPdf = (artifact: string, title: string) => {
  const bytes = Uint8Array.from(atob(artifact), (c) => c.charCodeAt(0));
  const link = window.document.createElement("a");
  link.href = URL.createObjectURL(
    new Blob([bytes], { type: "application/pdf" }),
  );
  link.download = `${title}.pdf`;
  link.click();
  URL.revokeObjectURL(link.href);
};

export default function DocumentWorkspace({ id }: { id: string }) {
  const { t, i18n } = useTranslation();
  const { data: me } = useMe();
  const document = useDocument(id);
  const save = useSave(id);
  const changeset = usePendingChangeset(id);
  const designEdit = useDesignDocument();
  const setMaster = useSetMaster();
  const exportPdf = useExportPdf();
  const remove = useDeleteDocument();
  const [, setParams] = useSearchParams();
  const saves = useSaves(id);
  const saving =
    useIsMutating({
      mutationKey: editDocumentMutationOptions.mutationKey,
      predicate: ({ state }) => (state.variables as { id: string }).id === id,
    }) > 0;
  const [pages, setPages] = useState(1);
  const panel = useEditorStore((state) => state.panel);
  const details = useEditorStore((state) => state.details);
  const showPanel = useEditorStore((state) => state.showPanel);
  const reset = useEditorStore((state) => state.reset);

  useEffect(() => reset, [reset]);

  if (document.isPending)
    return <StateMessage>{t("common.loading")}</StateMessage>;
  if (document.isError)
    return (
      <StateMessage tone="error">
        {t("documents.loadFailed", { reason: document.error.message })}
      </StateMessage>
    );

  const record = document.data;
  const shown = { ...record, body: record.pending_body ?? record.body };
  const pending = (changeset?.changeset.edits ?? []).flatMap(
    (edit) => pathOf(edit) ?? [],
  );
  const source = `user:${me?.id ?? "owner"}`;
  const entry = details && entryAt(shown.body.content.blocks, details)?.item;
  const tab: Panel = panel === "entry" && !entry ? "design" : panel;
  const failure = [saves.at(-1), designEdit, setMaster].find(
    (result) => result?.status === "error",
  )?.error;
  const status = saving
    ? { text: t("documents.status.saving"), tone: "text-ink-3" }
    : failure
      ? {
          text: t("documents.status.failed", { reason: failure.message }),
          tone: "text-crit",
        }
      : exportPdf.error
        ? {
            text: t("documents.status.exportFailed", {
              reason: exportPdf.error.message,
            }),
            tone: "text-crit",
          }
        : remove.error
          ? {
              text: t("documents.status.deleteFailed", {
                reason: remove.error.message,
              }),
              tone: "text-crit",
            }
          : pages > 1
            ? {
                text: t("documents.status.runsOnto", { count: pages }),
                tone: "text-warn",
              }
            : saves.some((save) => save.status === "success")
              ? { text: t("documents.status.saved"), tone: "text-ok" }
              : { text: t("documents.status.fits"), tone: "text-ink-3" };

  return (
    <div className="flex flex-wrap items-start gap-6">
      <section
        aria-labelledby="prev-h"
        className="flex min-w-0 flex-[3_1_560px] flex-col gap-3"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-0.5">
            <h2
              id="prev-h"
              className="m-0 flex items-center gap-2.5 text-xl font-semibold"
            >
              {record.title}
              {record.master && (
                <span className="bg-warn-bg text-amber rounded-full px-2.5 py-0.5 text-xs font-semibold">
                  {t("documents.master")}
                </span>
              )}
            </h2>
            <span className="text-ink-3 text-sm">
              {t("documents.meta", {
                when: relativeDay(record.updated_at, i18n.language),
              })}
              {" · "}
              <span
                className={cn(
                  "font-semibold",
                  record.pending_changesets > 0 ? "text-warn" : "text-ok",
                )}
              >
                {record.pending_changesets > 0
                  ? t("documents.check.changes", {
                      count: record.pending_changesets,
                    })
                  : t("documents.check.pages", { count: pages })}
              </span>
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {!record.master && (
              <button
                type="button"
                disabled={setMaster.isPending}
                onClick={() => setMaster.mutate(id)}
                className={buttonClass()}
              >
                {t("documents.setMaster")}
              </button>
            )}
            <button
              type="button"
              disabled={exportPdf.isPending}
              onClick={() =>
                exportPdf.mutate(id, {
                  onSuccess: ({ artifact }) =>
                    downloadPdf(artifact, record.title),
                })
              }
              className={buttonClass()}
            >
              {t("documents.export")}
            </button>
            <button
              type="button"
              disabled={record.master || remove.isPending}
              title={
                record.master
                  ? t(`documents.deleteMaster.${record.kind}`)
                  : undefined
              }
              onClick={() => {
                if (
                  window.confirm(
                    t("documents.confirmDelete", { name: record.title }),
                  )
                )
                  remove.mutate(id, {
                    onSuccess: () => setParams({ kind: record.kind }),
                  });
              }}
              className={buttonClass("danger")}
            >
              {t("documents.delete")}
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5">
          <span className="text-ink-3 text-[13px]">{t("documents.hint")}</span>
          <span
            role="status"
            className={cn("text-[13px] font-semibold", status.tone)}
          >
            {status.text}
          </span>
        </div>
        <DocumentPage
          record={shown}
          source={source}
          pending={pending}
          onEdit={save}
          pages={pages}
          onPages={setPages}
        />
        <div className="text-ink-3 flex flex-wrap gap-x-5 gap-y-2 text-[13px]">
          <span className="inline-flex items-center gap-2">
            <span
              aria-hidden="true"
              className="h-2.5 w-4 rounded-sm bg-[rgba(245,158,11,0.30)]"
            />
            {t("documents.legend.reworded")}
          </span>
          <span>{t("documents.legend.keys")}</span>
        </div>
      </section>

      <section
        aria-label={t("documents.tools")}
        className="bg-panel border-hair shadow-card flex min-w-0 flex-[2_1_340px] flex-col rounded-xl border"
      >
        <RadixTabs.Root
          value={tab}
          onValueChange={(next) => showPanel(next as Panel)}
          className="flex flex-col"
        >
          <RadixTabs.List
            aria-label={t("documents.tools")}
            className="border-hair-soft flex gap-1 border-b px-3 pt-1.5"
          >
            {(
              ["design", ...(entry ? ["entry"] : []), "assistant"] as Panel[]
            ).map((name) => (
              <RadixTabs.Trigger key={name} value={name} className={tabClass}>
                {t(`documents.panels.${name}`)}
              </RadixTabs.Trigger>
            ))}
          </RadixTabs.List>
          <RadixTabs.Content
            value="design"
            aria-label={t("documents.panels.design")}
          >
            <DesignPanel
              document={shown}
              onDesign={(design) =>
                designEdit.mutate({
                  id,
                  edits: [{ kind: "update_design", design }],
                })
              }
              onEdit={save}
            />
          </RadixTabs.Content>
          {entry && details && (
            <RadixTabs.Content
              value="entry"
              aria-label={t("documents.panels.entryDetails")}
            >
              <EntryPanel
                document={shown}
                path={details}
                source={source}
                onEdit={save}
              />
            </RadixTabs.Content>
          )}
          <RadixTabs.Content
            value="assistant"
            aria-label={t("documents.panels.assistant")}
          >
            <AssistantPanel document={record} />
          </RadixTabs.Content>
        </RadixTabs.Root>
      </section>
    </div>
  );
}
