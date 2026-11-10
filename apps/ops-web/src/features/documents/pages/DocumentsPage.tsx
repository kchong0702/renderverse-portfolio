import { FileUp, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { useMe } from "@/features/auth";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import { Tab, TabList, Tabs } from "@/shared/components/Tabs";
import { cn } from "@/shared/lib/cn";
import type { DocumentKind } from "../api/documents";
import DocumentWorkspace from "../components/DocumentWorkspace";
import { useCreateDocument, useDocuments } from "../hooks/useDocuments";
import { starterBody } from "../lib/starters";

const KINDS: DocumentKind[] = ["resume", "cover_letter", "cv"];

export default function DocumentsPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const documents = useDocuments();
  const create = useCreateDocument();
  const { data: me } = useMe();
  const kind = KINDS.find((k) => k === params.get("kind")) ?? "resume";
  const ofKind = documents.data?.filter((d) => d.kind === kind) ?? [];
  const selected = ofKind.find((d) => d.id === params.get("doc")) ?? ofKind[0];

  const startNew = () =>
    create.mutate(
      {
        title: t(`documents.untitled.${kind}`),
        body: starterBody(
          kind,
          {
            name: t("documents.starter.name"),
            greeting: t("documents.starter.greeting"),
            closing: t("documents.starter.closing"),
          },
          `user:${me?.id ?? "owner"}`,
        ),
      },
      { onSuccess: (document) => setParams({ kind, doc: document.id }) },
    );

  return (
    <>
      <PageHeader
        title={t("documents.pageTitle")}
        subtitle={t("documents.subtitle")}
        actions={
          <Link to="/documents/import" className={buttonClass()}>
            <FileUp size={16} />
            {t("documents.import")}
          </Link>
        }
      />
      <PageBody>
        {documents.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : documents.isError ? (
          <StateMessage tone="error">
            {t("documents.listFailed", { reason: documents.error.message })}
          </StateMessage>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-4">
              <Tabs
                value={kind}
                onValueChange={(next) => setParams({ kind: next })}
              >
                <TabList variant="pill" aria-label={t("documents.kinds.label")}>
                  {KINDS.map((k) => (
                    <Tab key={k} value={k}>
                      {t(`documents.kinds.${k}`)}{" "}
                      <span className="text-ink-3 font-medium">
                        {documents.data.filter((d) => d.kind === k).length}
                      </span>
                    </Tab>
                  ))}
                </TabList>
              </Tabs>
              <div
                role="group"
                aria-label={t("documents.list")}
                className="flex flex-wrap gap-2"
              >
                {ofKind.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    aria-pressed={d.id === selected?.id}
                    onClick={() => setParams({ kind, doc: d.id })}
                    className={cn(
                      "inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-full border px-3.5 text-sm",
                      d.id === selected?.id
                        ? "bg-primary text-on-primary border-primary font-semibold"
                        : "border-hair text-ink-2 font-medium",
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn(
                        "size-2 rounded-full",
                        d.pending_changesets > 0 ? "bg-warn" : "bg-ok",
                      )}
                    />
                    {d.title}
                  </button>
                ))}
                <button
                  type="button"
                  disabled={create.isPending}
                  onClick={startNew}
                  className="border-hair text-ink-2 inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-full border border-dashed px-3.5 text-sm font-medium disabled:opacity-60"
                >
                  <Plus size={15} />
                  {t("documents.new")}
                </button>
              </div>
            </div>
            {create.isError && (
              <p role="alert" className="text-crit m-0 text-sm">
                {t("documents.createFailed", { reason: create.error.message })}
              </p>
            )}
            {selected ? (
              <DocumentWorkspace key={selected.id} id={selected.id} />
            ) : (
              <StateMessage>{t(`documents.empty.${kind}`)}</StateMessage>
            )}
          </>
        )}
      </PageBody>
    </>
  );
}
