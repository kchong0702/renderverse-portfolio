import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import type { DocumentRecord } from "../api/documents";
import { useRender } from "../hooks/useDocuments";

export default function DocumentPreview({
  document,
}: {
  document: DocumentRecord;
}) {
  const { t } = useTranslation();
  const render = useRender(document.id, document.updated_at);
  const url = useMemo(() => {
    if (!render.data) return null;
    const bytes = Uint8Array.from(atob(render.data.artifact), (c) =>
      c.charCodeAt(0),
    );
    return URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
  }, [render.data]);

  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );

  const report = render.data?.report;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span role="status" className="text-ink-3 text-sm">
          {render.isFetching
            ? t("documents.preview.printing")
            : render.isError
              ? t("documents.preview.failed", { reason: render.error.message })
              : report &&
                [
                  t("documents.preview.pages", { count: report.pages }),
                  report.warnings.length > 0 &&
                    t("documents.preview.warnings", {
                      count: report.warnings.length,
                    }),
                ]
                  .filter(Boolean)
                  .join(" · ")}
        </span>
        {url && (
          <a
            href={url}
            download={`${document.title}.pdf`}
            className={buttonClass()}
          >
            {t("documents.preview.export")}
          </a>
        )}
      </div>
      <div className="bg-well border-hair flex min-h-[560px] items-stretch overflow-hidden rounded-xl border">
        {url ? (
          <iframe
            title={t("documents.preview.title", { title: document.title })}
            src={url}
            className="min-h-[720px] w-full border-0"
          />
        ) : (
          <p className="text-ink-3 m-auto max-w-sm p-6 text-center text-sm">
            {render.isError
              ? t("documents.preview.unavailable")
              : t("documents.preview.printing")}
          </p>
        )}
      </div>
    </div>
  );
}
