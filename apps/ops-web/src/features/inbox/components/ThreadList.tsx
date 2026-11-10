import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { daysAgo } from "../lib/dates";
import type { Thread } from "../lib/threads";

function receivedLabel(
  received: Date,
  language: string,
  yesterday: string,
): string {
  const days = daysAgo(received);
  if (days === 0)
    return received.toLocaleTimeString(language, {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    });
  if (days === 1) return yesterday;
  if (days < 7)
    return received.toLocaleDateString(language, { weekday: "short" });
  return received.toLocaleDateString(language, {
    day: "numeric",
    month: "short",
  });
}

interface ThreadListProps {
  threads: Thread[];
  selectedId: string;
  onSelect: (threadId: string) => void;
}

export default function ThreadList({
  threads,
  selectedId,
  onSelect,
}: ThreadListProps) {
  const { t, i18n } = useTranslation();

  return (
    <ul
      aria-label={t("inbox.threads")}
      className="bg-panel border-hair shadow-card m-0 list-none overflow-hidden rounded-xl border p-0"
    >
      {threads.map((thread) => (
        <li key={thread.thread_id}>
          <button
            type="button"
            aria-pressed={thread.thread_id === selectedId}
            onClick={() => onSelect(thread.thread_id)}
            className={cn(
              "border-hair-soft text-ink flex w-full cursor-pointer flex-col gap-1 border-b px-[18px] py-4 text-left",
              thread.thread_id === selectedId
                ? "bg-hair-soft"
                : "bg-transparent",
            )}
          >
            <span className="flex justify-between gap-2.5">
              <span className={thread.unread ? "font-bold" : "font-medium"}>
                {thread.application?.company ?? thread.from_name}
              </span>
              <span className="text-ink-3 shrink-0 text-[13px]">
                {receivedLabel(
                  new Date(thread.received_at),
                  i18n.language,
                  t("inbox.yesterday"),
                )}
              </span>
            </span>
            <span className="text-ink-2 text-[14px]">
              {thread.subject || t("inbox.noSubject")}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
