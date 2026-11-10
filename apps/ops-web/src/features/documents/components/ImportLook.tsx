import { PAGE_MM, type PageSize } from "@renderverse/document-renderer";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { buttonClass } from "@/shared/components/button";
import StateMessage from "@/shared/components/StateMessage";
import { cn } from "@/shared/lib/cn";
import type { DocumentImport } from "../api/documents";
import {
  useCancelImport,
  useDeleteDocument,
  useDesignDocument,
  useDocument,
} from "../hooks/useDocuments";
import { sourceKey } from "../lib/sources";
import { families, familyOf } from "../lib/templates";
import ResumePreview from "./ResumePreview";

const cited = (node: unknown): number =>
  Array.isArray(node)
    ? node.reduce((sum: number, item) => sum + cited(item), 0)
    : node && typeof node === "object"
      ? Object.values(node).reduce(
          (sum: number, value) => sum + cited(value),
          "src" in node &&
            Array.isArray(node.src) &&
            node.src.some((source) => sourceKey(source) === "upload")
            ? 1
            : 0,
        )
      : 0;

export default function ImportLook({
  upload,
  documentId,
}: {
  upload: DocumentImport;
  documentId: string;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const draft = useDocument(documentId);
  const design = useDesignDocument();
  const remove = useDeleteDocument();
  const cancel = useCancelImport();
  const [picked, setPicked] = useState<string>();
  const [sized, setSized] = useState<PageSize>();

  if (draft.isPending)
    return <StateMessage>{t("common.loading")}</StateMessage>;
  if (draft.isError)
    return (
      <StateMessage tone="error">
        {t("documents.loadFailed", { reason: draft.error.message })}
      </StateMessage>
    );

  const record = draft.data;
  const current = record.body.design;
  const template = picked ?? current.template;
  const size = sized ?? current.page_size;
  const look = familyOf(template);
  const suggestion = upload.suggestion;
  const suggested = suggestion && familyOf(suggestion.template);
  const listed = (items: string[]) =>
    items.length > 1
      ? t("documents.importPage.facts.and", {
          items: items.slice(0, -1).join(", "),
          last: items.at(-1),
        })
      : items[0];
  const lookOf = (id: string) => ({
    ...record.body,
    design: {
      ...current,
      template: id,
      page_size: size,
      accent: id === current.template ? current.accent : null,
    },
  });
  const blocks = record.body.content.blocks;
  const jobs = blocks.flatMap((b) => (b.kind === "experience" ? b.items : []));
  const kinds = (
    [
      ["role", jobs.length],
      ["achievement", jobs.flatMap((job) => job.bullets ?? []).length],
      [
        "skill",
        blocks.flatMap((b) =>
          b.kind === "skills" ? b.items.flatMap((skill) => skill.items) : [],
        ).length,
      ],
      [
        "degree",
        blocks.flatMap((b) => (b.kind === "education" ? b.items : [])).length,
      ],
    ] as const
  )
    .filter(([, count]) => count > 0)
    .map(([kind, count]) => t(`documents.importPage.facts.${kind}`, { count }));
  const failure = design.error ?? remove.error;
  const busy = design.isPending || remove.isPending;
  const to = `/documents?kind=${record.kind}&doc=${record.id}`;

  return (
    <>
      <div className="bg-panel border-hair shadow-card flex flex-wrap items-center justify-between gap-x-6 gap-y-3 rounded-xl border px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="bg-ok-bg text-ok flex size-8 flex-none items-center justify-center rounded-full">
            <svg
              aria-hidden="true"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m5 12 5 5 9-10" />
            </svg>
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="font-semibold">
              {kinds.length > 0
                ? t("documents.importPage.facts.checked", {
                    count: cited(blocks),
                    kinds: listed(kinds),
                  })
                : t("documents.importPage.facts.total", {
                    count: cited(blocks),
                  })}
            </span>
            <span className="text-ink-3 text-[13px]">
              {upload.media_type === "application/pdf"
                ? t("documents.importPage.facts.pdf")
                : t("documents.importPage.facts.word")}
            </span>
          </span>
        </div>
        <Link to={to} className={buttonClass()}>
          {t("documents.importPage.facts.review")}
        </Link>
      </div>

      <div className="flex flex-wrap items-start gap-6">
        <section
          aria-labelledby="look-h"
          className="flex min-w-0 flex-[3_1_560px] flex-col gap-4"
        >
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
            <div className="flex min-w-0 flex-col gap-0.5">
              <h2 id="look-h" className="m-0 text-xl/[1.6] font-semibold">
                {t("documents.importPage.look.title")}
              </h2>
              <span className="text-ink-3 text-sm/[1.6]">
                {t("documents.importPage.look.hint")}
              </span>
            </div>
            <div
              role="group"
              aria-label={t("documents.design.pageSize")}
              className="bg-chip flex rounded-[10px] p-[3px]"
            >
              {(["a4", "letter"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={option === size}
                  onClick={() => setSized(option)}
                  className={cn(
                    "min-h-9 cursor-pointer rounded-lg border-0 px-4 text-sm",
                    option === size
                      ? "bg-panel text-ink shadow-card font-semibold"
                      : "text-ink-3 bg-transparent font-medium",
                  )}
                >
                  {t(`documents.design.pageSizes.${option}`)}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(190px,1fr))] gap-3.5">
            {families.map((family) => {
              const id =
                family.id === look.id
                  ? template
                  : family.id === suggested?.id
                    ? suggestion!.template
                    : family.id;
              return (
                <button
                  key={family.id}
                  type="button"
                  aria-pressed={family.id === look.id}
                  onClick={() => setPicked(id)}
                  className={cn(
                    "bg-panel text-ink flex cursor-pointer flex-col gap-2.5 rounded-xl border p-2 text-left",
                    family.id === look.id
                      ? "border-amber shadow-[0_0_0_1px_var(--color-amber)]"
                      : "border-hair",
                  )}
                >
                  <ResumePreview
                    aria-hidden="true"
                    document={lookOf(id)}
                    className="border-hair-soft aspect-[4/3] w-full rounded-lg border"
                  />
                  <span className="flex flex-col gap-0.5 px-1 pb-1">
                    <span className="flex items-center gap-2 text-sm/[1.6] font-semibold">
                      {family.name}
                      {family.id === suggested?.id && (
                        <span className="bg-warn-bg text-amber rounded-full px-2 py-px text-xs font-semibold">
                          {t("documents.importPage.look.suggested")}
                        </span>
                      )}
                    </span>
                    <span className="text-ink-3 text-[13px] leading-[1.4]">
                      {family.description}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section
          aria-labelledby="pick-h"
          className="flex min-w-0 flex-[2_1_380px] flex-col gap-4"
        >
          <div className="flex flex-col gap-0.5">
            <h2 id="pick-h" className="m-0 text-xl/[1.6] font-semibold">
              {t("documents.importPage.look.picked", {
                name: look.name,
                size: t(`documents.design.pageSizes.${size}`),
              })}
            </h2>
            <span className="text-ink-3 text-sm/[1.6]">
              {suggestion?.template === template
                ? t(
                    suggestion.traits.length > 0
                      ? "documents.importPage.look.becauseWith"
                      : "documents.importPage.look.because",
                    {
                      file: t(
                        upload.media_type === "application/pdf"
                          ? "documents.importPage.look.files.pdf"
                          : "documents.importPage.look.files.word",
                      ),
                      columns: t(
                        `documents.importPage.look.columns.${suggestion.columns}`,
                      ),
                      traits: listed(
                        suggestion.traits.map((trait) =>
                          t(`documents.importPage.look.traits.${trait}`),
                        ),
                      ),
                    },
                  )
                : t("documents.importPage.look.note", {
                    description: look.description,
                  })}
            </span>
          </div>
          <div className="bg-well flex justify-center rounded-[14px] p-6">
            <ResumePreview
              role="img"
              aria-label={t("documents.importPage.look.page", {
                name: look.name,
              })}
              document={lookOf(template)}
              className="w-full max-w-[440px] shadow-[0_4px_18px_rgba(28,25,23,0.10)]"
              style={{ aspectRatio: PAGE_MM[size].join(" / ") }}
            />
          </div>
          <div className="flex flex-wrap gap-2.5">
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                design.mutate(
                  {
                    id: record.id,
                    edits: [
                      {
                        kind: "update_design",
                        design: lookOf(template).design,
                      },
                    ],
                  },
                  {
                    onSuccess: () => {
                      navigate(to);
                      cancel.mutate(upload.id);
                    },
                  },
                )
              }
              className="bg-primary text-on-primary inline-flex min-h-11 cursor-pointer items-center rounded-lg px-5 text-sm font-semibold disabled:cursor-default disabled:opacity-60 border-0"
            >
              {t("documents.importPage.look.use", { name: look.name })}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                remove.mutate(record.id, {
                  onSuccess: () => {
                    navigate("/documents");
                    cancel.mutate(upload.id);
                  },
                })
              }
              className="border-hair bg-panel text-ink inline-flex min-h-11 cursor-pointer items-center rounded-lg px-5 text-sm font-semibold disabled:cursor-default disabled:opacity-60 border"
            >
              {t("documents.importPage.cancel")}
            </button>
          </div>
          {failure && (
            <p role="alert" className="text-crit m-0 text-sm">
              {t("documents.status.failed", { reason: failure.message })}
            </p>
          )}
        </section>
      </div>
    </>
  );
}
