import { useTranslation } from "react-i18next";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import StateMessage from "@/shared/components/StateMessage";
import type { ChangesetStatus, DocumentRecord, Edit } from "../api/documents";
import { useChangesets, useDecideChangeset } from "../hooks/useDocuments";
import {
  blockKind,
  fieldKey,
  htmlToText,
  newText,
  nodeAt,
} from "../lib/fields";

const STATUS_TONE = {
  pending: "warn",
  accepted: "ok",
  rejected: "neutral",
} as const;

export default function ChangesPanel({
  document,
}: {
  document: DocumentRecord;
}) {
  const documentId = document.id;
  const { t } = useTranslation();
  const changesets = useChangesets(documentId);
  const decide = useDecideChangeset();

  const blocks = document.body.content.blocks;
  const kindLabel = (kind: string) => {
    const known = blockKind(kind);
    return known ? t(`documents.blocks.${known}`) : kind;
  };
  const blockLabel = (id: string) =>
    kindLabel(blocks.find((block) => block.id === id)?.kind ?? id);
  const fieldLabel = (path: string) => {
    const key = fieldKey(path);
    return key ? t(`documents.fields.${key}`) : blockLabel(path.split("/")[1]);
  };
  const describe = (edit: Edit) => {
    switch (edit.kind) {
      case "update_field":
        return t("documents.changes.update", {
          field: fieldLabel(edit.path),
          text: htmlToText(newText(edit.value)),
        });
      case "insert_block":
        return t("documents.changes.insertBlock", {
          kind: kindLabel(edit.block.kind),
        });
      case "insert_item":
        return t("documents.changes.insertItem", {
          parent: fieldLabel(edit.parent),
        });
      case "move":
        return t("documents.changes.move", {
          item: fieldLabel(edit.path),
          text: htmlToText(newText(nodeAt(blocks, edit.path))),
        });
      case "delete":
        return t("documents.changes.delete", {
          item: fieldLabel(edit.path),
          text: htmlToText(newText(nodeAt(blocks, edit.path))),
        });
      case "update_visibility":
        return t(
          edit.hidden ? "documents.changes.hide" : "documents.changes.show",
          { block: blockLabel(edit.block) },
        );
      case "update_design":
        return t("documents.changes.design");
    }
  };
  const status = (answer: ChangesetStatus) => (
    <Badge tone={STATUS_TONE[answer]}>
      {t(`documents.changes.status.${answer}`)}
    </Badge>
  );

  if (changesets.isPending)
    return <StateMessage>{t("common.loading")}</StateMessage>;
  if (changesets.isError)
    return (
      <StateMessage tone="error">
        {t("documents.changes.loadFailed", {
          reason: changesets.error.message,
        })}
      </StateMessage>
    );
  if (changesets.data.length === 0)
    return <StateMessage>{t("documents.changes.empty")}</StateMessage>;

  return (
    <div className="flex flex-col gap-5">
      {decide.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("documents.changes.failed", { reason: decide.error.message })}
        </p>
      )}
      {changesets.data.map(({ id, changeset, created_at }) => (
        <section
          key={id}
          aria-label={changeset.reason}
          className="border-hair overflow-hidden rounded-xl border"
        >
          <div className="bg-well flex flex-wrap items-center gap-3 px-4 py-3">
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="flex flex-wrap items-center gap-2 font-semibold">
                {changeset.reason}
                {status(changeset.status)}
              </span>
              <span className="text-ink-3 text-xs">
                {t("documents.changes.from", {
                  agent: changeset.agent,
                  date: new Date(created_at).toLocaleString(),
                })}
              </span>
            </div>
            {changeset.status === "pending" && (
              <span className="flex gap-2">
                {(["accepted", "rejected"] as const).map((answer) => (
                  <button
                    key={answer}
                    type="button"
                    disabled={decide.isPending}
                    onClick={() =>
                      decide.mutate({
                        id: documentId,
                        changesetId: id,
                        status: answer,
                      })
                    }
                    className={buttonClass(
                      answer === "accepted" ? "primary" : "secondary",
                    )}
                  >
                    {t(
                      `documents.changes.${answer === "accepted" ? "accept" : "reject"}`,
                    )}
                  </button>
                ))}
              </span>
            )}
          </div>
          {changeset.edits.map((edit, index) => (
            <div
              key={index}
              className="border-hair-soft flex flex-wrap items-center gap-3 border-t px-4 py-3"
            >
              <span className="min-w-0 flex-1 text-sm">{describe(edit)}</span>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
