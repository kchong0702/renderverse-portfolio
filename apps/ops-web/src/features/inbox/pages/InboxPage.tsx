import { RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { GoogleNotice, useSettings } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import MessageDetail from "../components/MessageDetail";
import MessageList from "../components/MessageList";
import { useInbox } from "../hooks/useInbox";

export default function InboxPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const settings = useSettings();
  const google = settings.data?.connections.find(({ id }) => id === "google");
  const account = google?.status === "connected" ? google.account : null;
  const inbox = useInbox(account !== null);
  const selected =
    inbox.data?.find((message) => message.id === params.get("message")) ??
    inbox.data?.[0];

  return (
    <>
      <PageHeader
        title={t("inbox.title")}
        subtitle={account && t("inbox.subtitle", { account })}
        actions={
          account && (
            <button
              type="button"
              className={buttonClass()}
              disabled={inbox.isFetching}
              onClick={() => void inbox.refetch()}
            >
              <RefreshCw aria-hidden size={16} />
              {t("inbox.refresh")}
            </button>
          )
        }
      />
      <PageBody>
        {settings.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : settings.isError ? (
          <StateMessage tone="error">
            {t("inbox.loadFailed", { reason: settings.error.message })}
          </StateMessage>
        ) : account === null ? (
          <GoogleNotice
            problem={
              google?.status === "not_configured"
                ? "not_configured"
                : "not_connected"
            }
            next="/inbox"
          />
        ) : inbox.isPending ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : inbox.isError ? (
          inbox.error instanceof ApiError && inbox.error.status === 409 ? (
            <GoogleNotice problem="expired" next="/inbox" />
          ) : (
            <StateMessage tone="error">
              {t("inbox.loadFailed", { reason: inbox.error.message })}
            </StateMessage>
          )
        ) : selected ? (
          <div className="flex flex-wrap items-start gap-4">
            <MessageList
              messages={inbox.data}
              selectedId={selected.id}
              onSelect={(id) => setParams({ message: id })}
            />
            <MessageDetail message={selected} account={account} />
          </div>
        ) : (
          <StateMessage>{t("inbox.empty")}</StateMessage>
        )}
      </PageBody>
    </>
  );
}
