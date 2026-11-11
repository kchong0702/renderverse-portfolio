import { useTranslation } from "react-i18next";
import TrashIcon from "@/shared/components/TrashIcon";
import { formatSize } from "@/shared/lib/size";
import { useAssets, useDeleteAsset } from "../hooks/useMedia";
import MediaThumb from "./MediaThumb";

const columns =
  "grid grid-cols-[64px_minmax(0,1fr)_minmax(0,96px)_40px] items-center gap-3 sm:grid-cols-[64px_minmax(0,1fr)_minmax(0,200px)_40px] sm:gap-4";

export default function MediaTab() {
  const { t, i18n } = useTranslation();
  const assets = useAssets();
  const remove = useDeleteAsset();

  return (
    <section aria-labelledby="media-heading" className="flex flex-col gap-4">
      <div className="flex flex-col gap-0.5">
        <h2 id="media-heading" className="text-ink m-0 text-base font-semibold">
          {t("portfolio.media.heading")}
        </h2>
        <span className="text-ink-3 text-sm">
          {t("portfolio.media.description")}
        </span>
      </div>
      <div className="bg-panel border-hair shadow-card overflow-hidden rounded-xl border">
        {assets.isError ? (
          <p role="alert" className="text-crit m-0 px-5 py-4 text-sm">
            {t("portfolio.media.loadFailed", { reason: assets.error.message })}
          </p>
        ) : !assets.data ? (
          <p className="text-ink-3 m-0 px-5 py-4 text-sm">
            {t("common.loading")}
          </p>
        ) : assets.data.length === 0 ? (
          <p className="text-ink-3 m-0 px-5 py-4 text-sm">
            {t("portfolio.media.empty")}
          </p>
        ) : (
          <div role="table" aria-labelledby="media-heading">
            <div
              role="row"
              className={`${columns} border-hair text-ink-3 border-b px-5 py-3 text-[13px] font-semibold`}
            >
              <span role="columnheader" className="col-span-2">
                {t("portfolio.media.file")}
              </span>
              <span role="columnheader">{t("portfolio.media.shownOn")}</span>
              <span role="columnheader" className="sr-only">
                {t("portfolio.table.deleteColumn")}
              </span>
            </div>
            {assets.data.map((asset) => (
              <div
                key={asset.id}
                role="row"
                className={`${columns} border-hair-soft border-b px-5 py-4 last:border-b-0`}
              >
                <span role="cell">
                  <MediaThumb asset={asset} />
                </span>
                <span role="cell" className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-ink truncate font-semibold">
                    {asset.filename}
                  </span>
                  <span className="text-ink-3 text-[13px]">
                    {t("portfolio.media.meta", {
                      type: t(`portfolio.media.types.${asset.media_type}`),
                      size: formatSize(asset.size, i18n.language),
                    })}
                  </span>
                  {remove.isError && remove.variables === asset.id && (
                    <span role="alert" className="text-crit text-sm">
                      {t("portfolio.media.deleteFailed", {
                        reason: remove.error.message,
                      })}
                    </span>
                  )}
                </span>
                <span role="cell" className="text-ink-2 min-w-0 text-sm">
                  {asset.projects.length > 0 ? (
                    asset.projects.map((project) => project.title).join(", ")
                  ) : (
                    <span className="text-ink-3">
                      {t("portfolio.media.notShown")}
                    </span>
                  )}
                </span>
                <span role="cell" className="flex justify-end">
                  {asset.projects.length === 0 && (
                    <button
                      type="button"
                      aria-label={t("portfolio.media.delete", {
                        name: asset.filename,
                      })}
                      onClick={() => {
                        if (
                          window.confirm(
                            t("portfolio.media.confirmDelete", {
                              name: asset.filename,
                            }),
                          )
                        )
                          remove.mutate(asset.id);
                      }}
                      className="text-ink-3 inline-flex size-10 cursor-pointer items-center justify-center rounded-lg"
                    >
                      <TrashIcon />
                    </button>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
