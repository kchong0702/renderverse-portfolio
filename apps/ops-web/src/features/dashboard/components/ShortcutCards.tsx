import { Sparkle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { Settings } from "@/features/settings";

const card =
  "bg-panel border-hair shadow-card text-ink flex flex-col gap-1.5 rounded-xl border px-[26px] py-[22px] no-underline";

export default function ShortcutCards({
  settings,
}: {
  settings: Settings | undefined;
}) {
  const { t } = useTranslation();
  const agent = settings?.job_agent;

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-5">
      <Link to="/jobs" className={card}>
        <span className="flex items-center gap-2 text-base font-semibold">
          <Sparkle size={15} className="text-amber" />
          {t("dashboard.agent.title")}
        </span>
        {agent && (
          <span className="text-ink-3 text-sm">
            {[
              t("dashboard.agent.daily", { time: agent.run_at.slice(0, 5) }),
              [agent.query, agent.location].filter(Boolean).join(", "),
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
        )}
      </Link>
      <Link to="/portfolio" className={card}>
        <span className="text-base font-semibold">
          {t("settings.connections.names.portfolio_site")}
        </span>
      </Link>
    </div>
  );
}
