import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import type { Draft, Release } from "../api/portfolio";
import { useMakeLive } from "../hooks/usePortfolio";

interface ReleasesAsideProps {
  draft: Draft;
  releases: Release[];
  publishError: string | null;
  limit?: number;
}

export default function ReleasesAside({
  draft,
  releases,
  publishError,
  limit,
}: ReleasesAsideProps) {
  const { t } = useTranslation();
  const makeLive = useMakeLive();
  const live = releases.find((release) => release.live);
  const row = "border-hair-soft flex items-center gap-3 border-b py-3";

  return (
    <aside
      aria-labelledby="releases-heading"
      className="bg-panel border-hair shadow-card flex max-w-[362px] flex-[1_1_302px] flex-col rounded-xl border px-5 py-[18px]"
    >
      <h2
        id="releases-heading"
        className="text-ink border-hair-soft m-0 border-b pb-2.5 text-[15px] font-semibold"
      >
        {t("portfolio.releases.heading")}
      </h2>
      {draft.changes.length > 0 && (
        <div className={row}>
          <span className="text-warn min-w-7 text-sm font-semibold tabular-nums">
            {draft.number}
          </span>
          <span className="flex flex-1 flex-col">
            <span className="text-warn font-semibold">
              {t("portfolio.releases.draft")}
            </span>
            <span className="text-ink-3 text-[13px]">
              {t("portfolio.releases.draftMeta", {
                count: draft.changes.length,
              })}
            </span>
          </span>
        </div>
      )}
      {releases.slice(0, limit).map((release) => {
        const earlier = !live || release.number < live.number;
        return (
          <div key={release.id} className={row}>
            <span
              className={cn(
                "min-w-7 text-sm font-semibold tabular-nums",
                release.live ? "text-ink" : "text-ink-3",
              )}
            >
              {release.number}
            </span>
            <span className="flex flex-1 flex-col">
              <span
                className={cn(
                  "font-semibold",
                  release.live ? "text-ink" : "text-ink-3",
                )}
              >
                {release.live
                  ? t("portfolio.releases.live")
                  : earlier
                    ? t("portfolio.releases.earlier")
                    : t("portfolio.releases.later")}
              </span>
              <span className="text-ink-3 text-[13px]">
                {t("portfolio.releases.published", {
                  day: new Date(release.published_at).getDate(),
                  month: new Date(release.published_at).toLocaleDateString(
                    "en",
                    { month: "short" },
                  ),
                })}
              </span>
            </span>
            {!release.live && (
              <button
                type="button"
                disabled={makeLive.isPending}
                onClick={() => makeLive.mutate(release.id)}
                className="text-amber min-h-8 cursor-pointer text-[13px] font-semibold disabled:cursor-default disabled:opacity-60"
              >
                {earlier
                  ? t("portfolio.releases.rollBack")
                  : t("portfolio.releases.makeLive")}
              </button>
            )}
          </div>
        );
      })}
      {publishError && (
        <span role="alert" className="text-crit pt-3 text-sm">
          {t("portfolio.releases.publishFailed", { reason: publishError })}
        </span>
      )}
      {makeLive.isError && (
        <span role="alert" className="text-crit pt-3 text-sm">
          {t("portfolio.releases.makeLiveFailed", {
            reason: makeLive.error.message,
          })}
        </span>
      )}
    </aside>
  );
}
