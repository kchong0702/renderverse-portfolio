import { FileUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import Panel from "@/shared/components/Panel";
import StateMessage from "@/shared/components/StateMessage";
import ImportSteps from "../components/ImportSteps";
import {
  useCancelImport,
  useImports,
  useStartImport,
  useTemplates,
} from "../hooks/useDocuments";

const STATUS_TONE = { pending: "warn", done: "ok", failed: "crit" } as const;

export default function ImportPage() {
  const { t } = useTranslation();
  const imports = useImports();
  const start = useStartImport();
  const cancel = useCancelImport();
  const templates = useTemplates("resume");
  const current = imports.data?.[0];

  return (
    <>
      <PageHeader
        title={t("documents.importPage.title")}
        subtitle={
          <>
            <Link to="/documents" className="text-ink-3">
              {t("documents.pageTitle")}
            </Link>
            {current && ` · ${current.filename}`}
          </>
        }
      />
      <PageBody>
        <ImportSteps current={current} />

        <Panel title={t("documents.importPage.upload.title")}>
          <p className="text-ink-3 m-0 text-sm">
            {t("documents.importPage.upload.hint")}
          </p>
          <label className={`${buttonClass("primary")} w-fit`}>
            <FileUp size={16} />
            {start.isPending
              ? t("documents.importPage.upload.uploading")
              : t("documents.importPage.upload.choose")}
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="sr-only"
              disabled={start.isPending}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) start.mutate(file);
                event.target.value = "";
              }}
            />
          </label>
          {start.isError && (
            <p role="alert" className="text-crit m-0 text-sm">
              {t("documents.importPage.upload.failed", {
                reason: start.error.message,
              })}
            </p>
          )}
        </Panel>

        {imports.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : imports.isError ? (
          <StateMessage tone="error">
            {t("documents.importPage.loadFailed", {
              reason: imports.error.message,
            })}
          </StateMessage>
        ) : (
          imports.data.length > 0 && (
            <Panel title={t("documents.importPage.files")}>
              <p className="bg-warn-bg text-warn m-0 rounded-lg px-4 py-3 text-sm">
                {t("documents.importPage.pending")}
              </p>
              <ul className="m-0 flex list-none flex-col p-0">
                {imports.data.map((row) => (
                  <li
                    key={row.id}
                    className="border-hair-soft flex flex-wrap items-center gap-3 border-b py-3 last:border-b-0"
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="flex flex-wrap items-center gap-2 font-semibold">
                        {row.filename}
                        <Badge tone={STATUS_TONE[row.status]}>
                          {t(`documents.importPage.status.${row.status}`)}
                        </Badge>
                      </span>
                      <span className="text-ink-3 text-xs">
                        {t("documents.importPage.uploaded", {
                          size: Math.max(1, Math.round(row.size / 1024)),
                          date: new Date(row.created_at).toLocaleString(),
                        })}
                        {row.error && ` · ${row.error}`}
                      </span>
                    </span>
                    {row.document_id && (
                      <Link
                        to={`/documents?doc=${row.document_id}`}
                        className={buttonClass("primary")}
                      >
                        {t("documents.importPage.open")}
                      </Link>
                    )}
                    <button
                      type="button"
                      disabled={cancel.isPending}
                      onClick={() => cancel.mutate(row.id)}
                      className={buttonClass()}
                    >
                      {t("documents.importPage.cancel")}
                    </button>
                  </li>
                ))}
              </ul>
            </Panel>
          )
        )}

        <Panel title={t("documents.importPage.look.title")}>
          <p className="text-ink-3 m-0 text-sm">
            {t("documents.importPage.look.hint")}
          </p>
          {templates.isError ? (
            <p role="alert" className="text-crit m-0 text-sm">
              {t("documents.design.templatesFailed", {
                reason: templates.error.message,
              })}
            </p>
          ) : (
            <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-3 p-0">
              {templates.data?.map((spec) => (
                <li
                  key={spec.id}
                  className="border-hair flex flex-col gap-1.5 rounded-[10px] border p-3"
                >
                  <span
                    aria-hidden="true"
                    className="h-1.5 w-1/2 rounded-sm"
                    style={{ background: spec.accent }}
                  />
                  <span className="text-sm font-semibold">{spec.name}</span>
                  <span className="text-ink-3 text-xs">{spec.description}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </PageBody>
    </>
  );
}
