import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useApplications } from "@/features/applications";
import { GoogleNotice, useGoogleAccount } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import FollowUps from "../components/FollowUps";
import MessageDetail from "../components/MessageDetail";
import ThreadList from "../components/ThreadList";
import { useInbox } from "../hooks/useInbox";
import { threadsOf } from "../lib/threads";

export default function InboxPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const { settings, account, problem } = useGoogleAccount();
  const inbox = useInbox(account !== null);
  const applications = useApplications();
  const threads = threadsOf(inbox.data ?? [], applications.data ?? []);
  const selected =
    threads.find(({ thread_id }) => thread_id === params.get("thread")) ??
    threads[0];

  return (
    <>
      <PageHeader
        title={t("inbox.title")}
        subtitle={account && t("inbox.subtitle")}
        actions={
          account && (
            <button
              type="button"
              className={buttonClass()}
              disabled={inbox.isFetching}
              onClick={() => void inbox.refetch()}
            >
              {t("inbox.sync")}
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
          <GoogleNotice problem={problem} next="/inbox" />
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
        ) : (
          <div className="flex flex-wrap items-start gap-6">
            <div className="flex max-w-[400px] min-w-0 flex-[1_1_320px] flex-col gap-4">
              {applications.isError ? (
                <StateMessage tone="error">
                  {t("applications.loadFailed", {
                    reason: applications.error.message,
                  })}
                </StateMessage>
              ) : (
                settings.data.automation.follow_up_reminders &&
                applications.data && (
                  <FollowUps applications={applications.data} />
                )
              )}
              {selected ? (
                <ThreadList
                  threads={threads}
                  selectedId={selected.thread_id}
                  onSelect={(thread) => setParams({ thread })}
                />
              ) : (
                <StateMessage>{t("inbox.empty")}</StateMessage>
              )}
            </div>
            {selected && <MessageDetail thread={selected} account={account} />}
          </div>
        )}
      </PageBody>
    </>
  );
}
