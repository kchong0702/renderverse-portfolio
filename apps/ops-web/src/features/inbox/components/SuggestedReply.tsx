import { Sparkle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useFreeSlots } from "@/features/calendar";
import { GoogleNotice } from "@/features/settings";
import { ApiError, RunFailed } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import { useReplyDraft, useSendReply } from "../hooks/useInbox";
import type { Thread } from "../lib/threads";

export default function SuggestedReply({ thread }: { thread: Thread }) {
  const { t, i18n } = useTranslation();
  const draft = useReplyDraft(thread.thread_id, thread.id);
  const send = useSendReply();
  const [edited, setEdited] = useState<string | null>(null);
  const [picked, setPicked] = useState<number[] | null>(null);
  const free = useFreeSlots(picked !== null);
  const label = (start: string) =>
    new Date(`${start.slice(0, 19)}Z`).toLocaleString(i18n.language, {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
      timeZone: "UTC",
    });
  const offered = draft.data ? draft.data.slots : [];
  const slots = (
    picked && free.data
      ? free.data.free_slots.filter(({ start }) =>
          picked.includes(Date.parse(start)),
        )
      : offered
  ).map(({ start }) => label(start));
  const email = draft.data
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
      ) : draft.error instanceof RunFailed ? (
        <>
          <p role="alert" className="m-0">
            {draft.error.message}
          </p>
          {draft.error.next && (
            <div>
              <Link
                to={`/${draft.error.next.screen}`}
                className={buttonClass()}
              >
                {draft.error.next.label}
              </Link>
            </div>
          )}
        </>
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
      ) : (
        <>
          {edited === null ? (
            <>
              <p className="m-0 whitespace-pre-line">{draft.data.body}</p>
              {offered.length > 0 && (
                <>
                  <div className="flex flex-wrap gap-2">
                    {picked && free.data
                      ? free.data.free_slots.map(({ start }) => (
                          <button
                            key={start}
                            type="button"
                            aria-pressed={picked.includes(Date.parse(start))}
                            onClick={() =>
                              setPicked(
                                picked.includes(Date.parse(start))
                                  ? picked.filter(
                                      (time) => time !== Date.parse(start),
                                    )
                                  : [...picked, Date.parse(start)],
                              )
                            }
                            className={cn(
                              "cursor-pointer rounded-lg border px-3 py-1.5 text-[14px] font-medium",
                              picked.includes(Date.parse(start))
                                ? "border-amber bg-panel text-ink"
                                : "border-hair text-ink-3 bg-transparent",
                            )}
                          >
                            {label(start)}
                          </button>
                        ))
                      : slots.map((slot) => (
                          <span
                            key={slot}
                            className="border-hair bg-panel rounded-lg border px-3 py-1.5 text-[14px] font-medium"
                          >
                            {slot}
                          </span>
                        ))}
                  </div>
                  {free.isError &&
                    (free.error instanceof ApiError &&
                    free.error.status === 409 ? (
                      <GoogleNotice
                        problem="reconnect"
                        reason={free.error.message}
                        next="/inbox"
                      />
                    ) : (
                      <p role="alert" className="text-crit m-0 text-[14px]">
                        {t("inbox.reply.timesFailed", {
                          reason: free.error.message,
                        })}
                      </p>
                    ))}
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
              {edited === null && offered.length > 0 && !free.data && (
                <button
                  type="button"
                  className={buttonClass()}
                  disabled={free.isFetching}
                  onClick={() =>
                    picked
                      ? void free.refetch()
                      : setPicked(offered.map(({ start }) => Date.parse(start)))
                  }
                >
                  {t("inbox.reply.pickTimes")}
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
