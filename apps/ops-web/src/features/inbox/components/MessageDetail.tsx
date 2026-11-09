import { ExternalLink } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import StateMessage from "@/shared/components/StateMessage";
import type { InboxMessage } from "../api/inbox";
import { useMessage } from "../hooks/useInbox";

interface MessageDetailProps {
  message: InboxMessage;
  account: string;
}

export default function MessageDetail({
  message,
  account,
}: MessageDetailProps) {
  const { t, i18n } = useTranslation();
  const headingId = useId();
  const detail = useMessage(message.id);

  return (
    <article
      aria-labelledby={headingId}
      className="bg-panel border-hair shadow-card flex min-w-0 flex-[999_1_420px] flex-col gap-5 rounded-xl border px-[30px] py-7"
    >
      <div className="flex flex-col gap-1">
        <h2
          id={headingId}
          className="m-0 text-[22px] leading-tight font-semibold"
        >
          {message.subject || t("inbox.noSubject")}
        </h2>
        <span className="text-ink-3 text-sm break-words">
          {[
            `${message.from_name} <${message.from_email}>`,
            new Date(message.received_at).toLocaleString(i18n.language, {
              dateStyle: "medium",
              timeStyle: "short",
              hourCycle: "h23",
            }),
            detail.data?.to && t("inbox.to", { to: detail.data.to }),
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
      </div>
      {detail.isPending ? (
        <p className="text-ink-3 m-0 text-sm">{t("common.loading")}</p>
      ) : detail.isError ? (
        <StateMessage tone="error">
          {t("inbox.messageFailed", { reason: detail.error.message })}
        </StateMessage>
      ) : (
        <p className="text-ink-2 m-0 max-w-[72ch] break-words whitespace-pre-line">
          {detail.data.body || message.snippet}
        </p>
      )}
      <div>
        <a
          href={`https://mail.google.com/mail/u/${account}/#all/${message.thread_id}`}
          target="_blank"
          rel="noreferrer"
          className={buttonClass()}
        >
          <ExternalLink aria-hidden size={16} />
          {t("inbox.openInGmail")}
        </a>
      </div>
    </article>
  );
}
