import { useTranslation } from "react-i18next";
import Badge from "@/shared/components/Badge";
import { cn } from "@/shared/lib/cn";
import type { InboxMessage } from "../api/inbox";

const DAY_MS = 86_400_000;

function receivedLabel(value: string, language: string): string {
  const received = new Date(value);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.floor((today.getTime() - received.getTime()) / DAY_MS) + 1;
  if (days <= 0)
    return received.toLocaleTimeString(language, {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    });
  if (days < 7)
    return received.toLocaleDateString(language, { weekday: "short" });
  return received.toLocaleDateString(language, {
    day: "numeric",
    month: "short",
  });
}

interface MessageListProps {
  messages: InboxMessage[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function MessageList({
  messages,
  selectedId,
  onSelect,
}: MessageListProps) {
  const { t, i18n } = useTranslation();

  return (
    <ul
      aria-label={t("inbox.messages")}
      className="bg-panel border-hair shadow-card m-0 flex max-w-[400px] flex-[1_1_300px] list-none flex-col overflow-hidden rounded-xl border p-0"
    >
      {messages.map((message) => (
        <li
          key={message.id}
          className="border-hair-soft border-t first:border-t-0"
        >
          <button
            type="button"
            aria-pressed={message.id === selectedId}
            onClick={() => onSelect(message.id)}
            className={cn(
              "text-ink flex w-full cursor-pointer flex-col gap-0.5 px-[18px] py-3.5 text-left",
              message.id === selectedId ? "bg-hair-soft" : "bg-transparent",
            )}
          >
            <span className="flex items-baseline justify-between gap-3">
              <span
                className={cn(
                  "truncate",
                  message.unread ? "font-bold" : "font-medium",
                )}
              >
                {message.from_name}
              </span>
              <span className="text-ink-3 shrink-0 text-xs">
                {receivedLabel(message.received_at, i18n.language)}
              </span>
            </span>
            <span className="text-ink-2 truncate text-sm">
              {message.subject || t("inbox.noSubject")}
            </span>
            <span className="flex items-center gap-2">
              <span className="text-ink-3 line-clamp-1 flex-1 text-[13px]">
                {message.snippet}
              </span>
              {message.unread && (
                <Badge tone="accent">{t("inbox.unread")}</Badge>
              )}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
