import { Sparkle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { GoogleNotice } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import { useReplyDraft, useSendReply } from "../hooks/useInbox";
import type { Thread } from "../lib/threads";

export default function SuggestedReply({ thread }: { thread: Thread }) {
  const { t, i18n } = useTranslation();
  const draft = useReplyDraft(thread.thread_id, thread.id);
  const send = useSendReply();
  const [edited, setEdited] = useState<string | null>(null);
  const slots =
    draft.data && !("status" in draft.data)
      ? draft.data.slots.map(({ start }) =>
          new Date(`${start.slice(0, 19)}Z`).toLocaleString(i18n.language, {
            weekday: "short",
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
            timeZone: "UTC",
          }),
        )
      : [];
  const email =
    draft.data && !("status" in draft.data)
      ? [draft.data.body, slots.join("\n")].filter(Boolean).join("\n\n")
      : "";

  return (
    <div className="bg-warn-bg flex flex-col gap-3 rounded-xl px-[18px] py-4">
      <span className="flex items-center gap-2 font-semibold">
        <span className="text-amber flex">
          <Sparkle aria-hidden size={16} />
        </span>
        {t("inbox.reply.title")}
      </span>
      {draft.isPending ? (
        <p className="text-ink-3 m-0 text-[14px]">
          {t("inbox.reply.drafting")}
        </p>
      ) : draft.isError ? (
        draft.error instanceof ApiError && draft.error.status === 409 ? (
          <GoogleNotice
            problem="reconnect"
            reason={draft.error.message}
            next="/inbox"
          />
        ) : (
          <p role="alert" className="text-crit m-0 text-[14px]">
            {t("inbox.reply.failed", { reason: draft.error.message })}
          </p>
        )
      ) : "status" in draft.data ? (
        <>
          <p role="alert" className="m-0">
            {draft.data.reason}
          </p>
          {draft.data.next && (
            <div>
              <Link to={`/${draft.data.next.screen}`} className={buttonClass()}>
                {draft.data.next.label}
              </Link>
            </div>
          )}
        </>
      ) : (
        <>
          {edited === null ? (
            <>
              <p className="m-0 whitespace-pre-line">{draft.data.body}</p>
              {slots.length > 0 && (
                <>
                  <div className="flex flex-wrap gap-2">
                    {slots.map((slot) => (
                      <span
                        key={slot}
                        className="border-hair bg-panel rounded-lg border px-3 py-1.5 text-[14px] font-medium"
                      >
                        {slot}
                      </span>
                    ))}
                  </div>
                  <span className="text-ink-3 text-[13px]">
                    {t("inbox.reply.note")}
                  </span>
                </>
              )}
            </>
          ) : (
            <textarea
              aria-label={t("inbox.reply.message")}
              value={edited}
              rows={8}
              disabled={send.isPending || send.isSuccess}
              onChange={(event) => setEdited(event.target.value)}
              className="border-hair bg-panel text-ink rounded-lg border px-3 py-2 text-[14px] leading-normal"
            />
          )}
          {send.isSuccess ? (
            <p role="status" className="text-ok m-0 text-[14px] font-semibold">
              {t("inbox.reply.sent")}
            </p>
          ) : (
            <div className="flex flex-wrap gap-2.5">
              <button
                type="button"
                className={buttonClass("primary")}
                disabled={send.isPending || !(edited ?? email).trim()}
                onClick={() =>
                  send.mutate({
                    threadId: thread.thread_id,
                    body: edited ?? email,
                  })
                }
              >
                <span className="text-amber-soft flex">
                  <Sparkle aria-hidden size={14} />
                </span>
                {t("inbox.reply.send")}
              </button>
              {edited === null && (
                <button
                  type="button"
                  className={buttonClass()}
                  onClick={() => setEdited(email)}
                >
                  {t("inbox.reply.edit")}
                </button>
              )}
            </div>
          )}
          {send.isError &&
            (send.error instanceof ApiError && send.error.status === 409 ? (
              <GoogleNotice
                problem="reconnect"
                reason={send.error.message}
                next="/inbox"
              />
            ) : (
              <p role="alert" className="text-crit m-0 text-[14px]">
                {t("inbox.reply.sendFailed", { reason: send.error.message })}
              </p>
            ))}
        </>
      )}
    </div>
  );
}
