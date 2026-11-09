import { Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import DraftTextField from "@/shared/components/DraftTextField";
import StateMessage from "@/shared/components/StateMessage";
import { Tab, TabList, TabPanel, Tabs } from "@/shared/components/Tabs";
import {
  useDeleteDocument,
  useDocument,
  useEditDocument,
  useRenameDocument,
  useSetMaster,
} from "../hooks/useDocuments";
import ChangesPanel from "./ChangesPanel";
import ContentPanel from "./ContentPanel";
import DesignPanel from "./DesignPanel";
import DocumentPreview from "./DocumentPreview";
import VersionsPanel from "./VersionsPanel";

const PANELS = ["content", "design", "changes", "versions"] as const;
type ToolPanel = (typeof PANELS)[number];

export default function DocumentWorkspace({ id }: { id: string }) {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const document = useDocument(id);
  const edit = useEditDocument();
  const rename = useRenameDocument();
  const setMaster = useSetMaster();
  const remove = useDeleteDocument();
  const panel: ToolPanel =
    PANELS.find((name) => name === params.get("panel")) ?? "content";

  if (document.isPending)
    return <StateMessage>{t("common.loading")}</StateMessage>;
  if (document.isError)
    return (
      <StateMessage tone="error">
        {t("documents.loadFailed", { reason: document.error.message })}
      </StateMessage>
    );

  const record = document.data;
  const failure = [edit, rename, setMaster, remove].find(
    (m) => m.isError,
  )?.error;

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(440px,100%),1fr))] items-start gap-6">
      <section
        aria-label={record.title}
        className="bg-panel border-hair shadow-card flex flex-col gap-4 rounded-xl border px-6 py-5"
      >
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex min-w-[220px] flex-1 items-end gap-2.5">
            <div className="flex-1">
              <DraftTextField
                label={t("documents.title")}
                value={record.title}
                maxLength={200}
                onSave={(title) => title && rename.mutate({ id, title })}
              />
            </div>
            {record.master && (
              <Badge tone="accent">{t("documents.master")}</Badge>
            )}
          </div>
          <div className="flex gap-2">
            {!record.master && (
              <button
                type="button"
                onClick={() => setMaster.mutate(id)}
                className={buttonClass()}
              >
                {t("documents.setMaster")}
              </button>
            )}
            <button
              type="button"
              aria-label={t("documents.delete", { title: record.title })}
              onClick={() => {
                if (
                  window.confirm(
                    t("documents.confirmDelete", { title: record.title }),
                  )
                )
                  remove.mutate(id, {
                    onSuccess: () => setParams({ kind: record.kind }),
                  });
              }}
              className="text-ink-3 hover:text-crit inline-flex size-10 cursor-pointer items-center justify-center rounded-lg"
            >
              <Trash2 size={18} />
            </button>
          </div>
        </div>
        <span role="status" className="text-ink-3 text-sm">
          {failure
            ? t("documents.save.failed", { reason: failure.message })
            : edit.isPending
              ? t("documents.save.saving")
              : record.pending_edits > 0
                ? t("documents.pendingEdits", { count: record.pending_edits })
                : t("documents.updated", {
                    date: new Date(record.updated_at).toLocaleString(),
                  })}
        </span>
        <DocumentPreview document={record} />
      </section>

      <section
        aria-label={t("documents.tools")}
        className="bg-panel border-hair shadow-card flex flex-col rounded-xl border"
      >
        <Tabs
          value={panel}
          onValueChange={(next) =>
            setParams((current) => {
              current.set("panel", next);
              return current;
            })
          }
        >
          <TabList aria-label={t("documents.tools")} className="px-5">
            {PANELS.map((name) => (
              <Tab key={name} value={name}>
                {name === "changes" && record.pending_edits > 0
                  ? t("documents.panels.changesCount", {
                      count: record.pending_edits,
                    })
                  : t(`documents.panels.${name}`)}
              </Tab>
            ))}
          </TabList>
          <div className="p-5">
            <TabPanel value="content">
              <ContentPanel
                document={record}
                onEdit={(edits) => edit.mutate({ id, edits })}
              />
            </TabPanel>
            <TabPanel value="design">
              <DesignPanel
                document={record}
                onChange={(design) =>
                  edit.mutate({
                    id,
                    edits: [{ kind: "update_design", design }],
                  })
                }
              />
            </TabPanel>
            <TabPanel value="changes">
              <ChangesPanel document={record} />
            </TabPanel>
            <TabPanel value="versions">
              <VersionsPanel documentId={id} />
            </TabPanel>
          </div>
        </Tabs>
      </section>
    </div>
  );
}
