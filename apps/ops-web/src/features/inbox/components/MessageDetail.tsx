import { ExternalLink } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { GoogleNotice } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import StateMessage from "@/shared/components/StateMessage";
import { useMessage } from "../hooks/useInbox";
import { daysAgo } from "../lib/dates";
import type { Thread } from "../lib/threads";
import SuggestedReply from "./SuggestedReply";

interface MessageDetailProps {
  thread: Thread;
  account: string;
  suggestsReplies: boolean;
}

export default function MessageDetail({
  thread,
  account,
  suggestsReplies,
}: MessageDetailProps) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const detail = useMessage(thread.id);
  const received = new Date(thread.received_at);
  const time = received.toLocaleTimeString(i18n.language, {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });

  return (
    <article
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex min-w-0 flex-[999_1_460px] flex-col gap-5 rounded-xl border px-[30px] py-[26px]"
    >
      <div className="flex flex-col gap-1">
        <h2 id={headingId} className="m-0 text-[20px] font-semibold">
          {thread.subject || t("inbox.noSubject")}
        </h2>
        <span className="text-ink-3 text-[14px] break-words">
          {[
            thread.from_name,
            daysAgo(received) === 0
              ? t("inbox.today", { time })
              : received.toLocaleString(i18n.language, {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                  hourCycle: "h23",
                }),
            thread.application &&
              t("inbox.linked", {
                role: thread.application.role,
                stage: t(`applications.stages.${thread.application.stage}`),
              }),
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
      </div>
      {detail.isPending ? (
        <p className="text-ink-3 m-0 text-[14px]">{t("common.loading")}</p>
      ) : detail.isError ? (
        detail.error instanceof ApiError && detail.error.status === 409 ? (
          <GoogleNotice
            problem="reconnect"
            reason={detail.error.message}
            next="/inbox"
          />
        ) : (
          <StateMessage tone="error">
            {t("inbox.messageFailed", { reason: detail.error.message })}
          </StateMessage>
        )
      ) : (
        <p className="text-ink-2 m-0 max-w-[72ch] break-words whitespace-pre-line">
          {detail.data.body || thread.snippet}
        </p>
      )}
      {suggestsReplies && thread.state === "needs_reply" ? (
        <SuggestedReply key={thread.id} thread={thread} />
      ) : (
        <div>
          <a
            href={`https://mail.google.com/mail/u/${account}/#all/${thread.thread_id}`}
            target="_blank"
            rel="noreferrer"
            className={buttonClass()}
          >
            <ExternalLink aria-hidden size={16} />
            {t("inbox.openInGmail")}
          </a>
        </div>
      )}
    </article>
  );
}
