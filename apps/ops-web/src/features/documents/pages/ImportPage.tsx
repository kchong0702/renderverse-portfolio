import { FileUp } from "lucide-react";
import { lazy, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { isActive } from "@/features/imports";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import StateMessage from "@/shared/components/StateMessage";
import ImportSteps from "../components/ImportSteps";
import {
  useCancelImport,
  useImports,
  useStartImport,
} from "../hooks/useDocuments";

const ImportLook = lazy(() => import("../components/ImportLook"));

export default function ImportPage() {
  const { t } = useTranslation();
  const imports = useImports();
  const start = useStartImport();
  const cancel = useCancelImport();
  const latest = imports.data?.[0];
  const current = latest?.status === "abandoned" ? undefined : latest;
  const reading = current !== undefined && isActive(current);
  const failure = start.isError
    ? t("documents.importPage.upload.failed", { reason: start.error.message })
    : current?.status === "failed"
      ? t("documents.importPage.readFailed", { reason: current.error })
      : null;

  return (
    <>
      <header className="bg-header border-hair flex min-h-16 flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b px-4 py-3.5 shell:px-10">
        <div className="flex min-w-0 items-baseline gap-2.5">
          <Link
            to="/documents"
            className="text-ink-3 text-sm/[1.6] no-underline"
          >
            {t("documents.pageTitle")}
          </Link>
          <span aria-hidden="true" className="text-ink-3">
            /
          </span>
          <h1 className="m-0 text-xl/[1.6] font-semibold">
            {t("documents.importPage.title")}
          </h1>
        </div>
        {current && (
          <span className="text-ink-3 text-sm/[1.6]">{current.filename}</span>
        )}
      </header>
      <PageBody wide>
        <ImportSteps read={!!current?.document_id} />
        {imports.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : imports.isError ? (
          <StateMessage tone="error">
            {t("documents.importPage.loadFailed", {
              reason: imports.error.message,
            })}
          </StateMessage>
        ) : (
          <>
            <div className="bg-panel border-hair shadow-card flex flex-wrap items-center justify-between gap-x-6 gap-y-3 rounded-xl border px-5 py-4">
              <div className="flex min-w-0 items-center gap-3">
                <span className="bg-chip text-ink-3 flex size-8 flex-none items-center justify-center rounded-full">
                  <FileUp size={16} />
                </span>
                <span className="flex min-w-0 flex-col">
                  <span className="font-semibold">
                    {t("documents.importPage.upload.title")}
                  </span>
                  {reading ? (
                    <span role="status" className="text-ink-3 text-[13px]">
                      {current.status === "queued" && current.error
                        ? t("documents.importPage.retrying", {
                            reason: current.error,
                          })
                        : t(
                            current.status === "queued"
                              ? "documents.importPage.queued"
                              : "documents.importPage.reading",
                          )}
                    </span>
                  ) : failure ? (
                    <span role="alert" className="text-crit text-[13px]">
                      {failure}
                    </span>
                  ) : (
                    <span className="text-ink-3 text-[13px]">
                      {t("documents.importPage.upload.hint")}
                    </span>
                  )}
                </span>
              </div>
              <div className="flex flex-wrap gap-2.5">
                {current && reading && (
                  <button
                    type="button"
                    disabled={cancel.isPending}
                    onClick={() => cancel.mutate(current.id)}
                    className={buttonClass()}
                  >
                    {t("documents.importPage.cancel")}
                  </button>
                )}
                <label className={buttonClass("primary")}>
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
              </div>
            </div>
            {current?.status === "done" && current.document_id && (
              <Suspense
                fallback={<StateMessage>{t("common.loading")}</StateMessage>}
              >
                <ImportLook upload={current} documentId={current.document_id} />
              </Suspense>
            )}
          </>
        )}
      </PageBody>
    </>
  );
}
