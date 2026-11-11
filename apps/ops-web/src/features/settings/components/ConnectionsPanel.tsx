import { useState } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import { TextField } from "@/shared/components/fields";
import { cn } from "@/shared/lib/cn";
import Panel from "@/shared/components/Panel";
import type { Connection } from "../api/settings";
import { useConnectJsearch, useDisconnectJsearch } from "../hooks/useSettings";

export default function ConnectionsPanel({
  connections,
}: {
  connections: Connection[];
}) {
  const { t } = useTranslation();
  const connect = useConnectJsearch();
  const disconnect = useDisconnectJsearch();
  const [apiKey, setApiKey] = useState<string | null>(null);
  const close = () => {
    setApiKey(null);
    connect.reset();
    disconnect.reset();
  };

  return (
    <Panel title={t("settings.connections.title")}>
      {connections.map((connection) => (
        <div
          key={connection.id}
          className="border-hair-soft flex flex-col gap-3.5 border-t pt-3.5"
        >
          <div className="flex items-center justify-between gap-3.5">
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
                {connection.status === "connected" && connection.quota
                  ? t("settings.connections.quota", { ...connection.quota })
                  : t(`settings.connections.status.${connection.status}`)}
              </span>
            </span>
            {connection.id === "jsearch" && apiKey === null && (
              <button
                type="button"
                onClick={() => setApiKey("")}
                className={buttonClass()}
              >
                {connection.status === "connected"
                  ? t("settings.connections.jsearch.change")
                  : t("settings.connections.jsearch.add")}
              </button>
            )}
          </div>
          {connection.id === "jsearch" && apiKey !== null && (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                connect.mutate(apiKey.trim(), { onSuccess: close });
              }}
              className="flex flex-col gap-3.5"
            >
              <TextField
                type="password"
                label={t("settings.connections.jsearch.key")}
                autoFocus
                required
                autoComplete="off"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
              {(connect.error ?? disconnect.error) && (
                <p role="alert" className="text-crit m-0 text-sm">
                  {t("settings.connections.jsearch.failed", {
                    reason: (connect.error ?? disconnect.error)?.message,
                  })}
                </p>
              )}
              <div className="flex gap-2.5">
                <button
                  type="submit"
                  disabled={connect.isPending || disconnect.isPending}
                  className={buttonClass("primary")}
                >
                  {t("settings.connections.jsearch.save")}
                </button>
                <button type="button" onClick={close} className={buttonClass()}>
                  {t("settings.connections.jsearch.cancel")}
                </button>
                {connection.status === "connected" && (
                  <button
                    type="button"
                    disabled={connect.isPending || disconnect.isPending}
                    onClick={() =>
                      disconnect.mutate(undefined, { onSuccess: close })
                    }
                    className={cn(buttonClass("danger"), "ml-auto")}
                  >
                    {t("settings.connections.jsearch.remove")}
                  </button>
                )}
              </div>
            </form>
          )}
        </div>
      ))}
    </Panel>
  );
}
