import { useTranslation } from "react-i18next";
import Badge from "@/shared/components/Badge";
import type { Draft } from "../api/portfolio";

export default function ChangesTab({ draft }: { draft: Draft }) {
  const { t } = useTranslation();

  return (
    <section
      aria-labelledby="changes-heading"
      className="flex min-w-0 flex-[999_1_560px] flex-col gap-4"
    >
      <div className="flex flex-col gap-0.5">
        <h2
          id="changes-heading"
          className="text-ink m-0 text-base font-semibold"
        >
          {t("portfolio.changes.heading", { number: draft.number })}
        </h2>
        <span className="text-ink-3 text-sm">
          {t("portfolio.changes.description")}
        </span>
      </div>
      <div className="bg-panel border-hair shadow-card overflow-hidden rounded-xl border">
        {draft.changes.length === 0 ? (
          <p className="text-ink-3 m-0 px-5 py-4 text-sm">
            {t("portfolio.changes.empty")}
          </p>
        ) : (
          <ul className="m-0 list-none p-0">
            {draft.changes.map((change) => (
              <li
                key={`${change.kind}-${change.id}`}
                className="border-hair-soft flex flex-wrap items-center gap-2.5 border-b px-5 py-4 last:border-b-0"
              >
                <span className="font-semibold">
                  {change.kind === "about"
                    ? t("portfolio.changes.about")
                    : change.name}
                </span>
                <span className="text-ink-3 text-[13px]">
                  {t(`portfolio.changes.kinds.${change.kind}`)}
                </span>
                <Badge tone={change.change === "removed" ? "neutral" : "warn"}>
                  {t(`portfolio.changes.types.${change.change}`)}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
