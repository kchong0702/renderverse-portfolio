import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import Panel from "@/shared/components/layout/Panel";
import type { Connection } from "../api/settings";

// Connect and disconnect actions arrive with each integration
export default function ConnectionsPanel({
  connections,
}: {
  connections: Connection[];
}) {
  const { t } = useTranslation();

  return (
    <Panel title={t("settings.connections.title")}>
      {connections.map((connection) => (
        <div
          key={connection.id}
          className="border-hair-soft flex items-center justify-between gap-3.5 border-t pt-3.5"
        >
          <span className="flex flex-col">
            <span className="font-semibold">
              {t(`settings.connections.names.${connection.id}`)}
            </span>
            <span
              className={cn(
                "text-sm",
                connection.status === "connected" ? "text-ok" : "text-ink-3",
              )}
            >
              {t(`settings.connections.status.${connection.status}`)}
            </span>
          </span>
        </div>
      ))}
    </Panel>
  );
}
