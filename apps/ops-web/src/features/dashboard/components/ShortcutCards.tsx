import { Sparkle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useIsAdmin } from "@/features/auth";
import type { JobRun } from "@/features/jobs";
import type { Preferences } from "@/features/preferences";
import { daysFromToday } from "@/shared/lib/dates";

const card =
  "bg-panel border-hair shadow-card text-ink flex flex-col gap-1.5 rounded-xl border px-[26px] py-[22px] no-underline";

export default function ShortcutCards({
  preferences,
  run,
}: {
  preferences: Preferences | undefined;
  run: JobRun | null | undefined;
}) {
  const { t } = useTranslation();
  const isAdmin = useIsAdmin();

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-5">
      <Link to="/jobs" className={card}>
        <span className="flex items-center gap-2 text-base font-semibold">
          <Sparkle size={15} className="text-amber" />
          {t("dashboard.agent.title")}
        </span>
        {preferences && (
          <span className="text-ink-3 text-sm">
            {[
              t("dashboard.agent.daily", {
                time: preferences.run_at.slice(0, 5),
              }),
              [preferences.target_roles, preferences.location]
                .filter(Boolean)
                .join(", "),
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
        )}
        {run && daysFromToday(run.finished_at) === 0 && (
          <span className="mt-1.5 tabular-nums">
            {t("dashboard.agent.today", {
              found: run.found,
              new: run.new,
              scored: run.scored_70,
            })}
          </span>
        )}
      </Link>
      {isAdmin && (
        <Link to="/portfolio" className={card}>
          <span className="text-base font-semibold">
            {t("settings.connections.names.portfolio_site")}
          </span>
        </Link>
      )}
    </div>
  );
}
