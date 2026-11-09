import { useIsMutating } from "@tanstack/react-query";
import { SquarePen, Sparkle } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import type { Widget } from "../api/assistant";
import { useAnswerTask, useSendMessage } from "../hooks/useAssistant";
import { useAssistantStore } from "../state/assistantStore";

const fieldClass =
  "border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 py-2 text-sm leading-normal disabled:opacity-60";

function ChatWidget({
  taskId,
  widget,
  live,
}: {
  taskId: string;
  widget: Widget;
  live: boolean;
}) {
  const { t } = useTranslation();
  const answer = useAnswerTask();
  const chatId = useAssistantStore((state) => state.chatId);
  const [input, setInput] = useState("");
  const labelId = useId();
  const asksInput = widget.input_placeholder !== null;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        answer.mutate({
          chatId,
          taskId,
          answer: { input: input.trim() || undefined, accept: true },
          shown: input.trim() || widget.submit_btn || t("assistant.send"),
        });
      }}
      className="border-hair flex flex-col gap-2 self-stretch rounded-xl border p-3"
    >
      {widget.label && (
        <p id={labelId} className="text-ink m-0 text-sm">
          {widget.label}
        </p>
      )}
      {live && widget.input_value !== null && (
        <input
          disabled
          value={widget.input_value}
          aria-labelledby={labelId}
          className={fieldClass}
        />
      )}
      {live && asksInput && (
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={widget.input_placeholder ?? undefined}
          aria-labelledby={labelId}
          disabled={answer.isPending}
          className={fieldClass}
        />
      )}
      {live && (
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={answer.isPending || (asksInput && !input.trim())}
            className={buttonClass("primary")}
          >
            {widget.submit_btn ?? t("assistant.send")}
          </button>
          {widget.cancel_btn !== null && (
            <button
              type="button"
              disabled={answer.isPending}
              onClick={() =>
                answer.mutate({
                  chatId,
                  taskId,
                  answer: { accept: false },
                  shown: widget.cancel_btn ?? "",
                })
              }
              className={buttonClass()}
            >
              {widget.cancel_btn}
            </button>
          )}
        </div>
      )}
      {answer.error && (
        <p role="alert" className="text-crit m-0 text-[13px]">
          {t("assistant.answerFailed", { reason: answer.error.message })}
        </p>
      )}
    </form>
  );
}

export default function AssistantDock({
  topic,
  suggestions,
}: {
  topic?: string;
  suggestions: string[];
}) {
  const { t, i18n } = useTranslation();
  const open = useAssistantStore((state) => state.open);
  const setOpen = useAssistantStore((state) => state.setOpen);
  const entries = useAssistantStore((state) => state.entries);
  const chatId = useAssistantStore((state) => state.chatId);
  const newChat = useAssistantStore((state) => state.newChat);
  const send = useSendMessage();
  const busy = useIsMutating({ mutationKey: ["assistant"] }) > 0;
  const [draft, setDraft] = useState("");
  const toggleRef = useRef<HTMLButtonElement>(null);
  const transcriptRef = useRef<HTMLOListElement>(null);
  const panelId = useId();

  useEffect(() => {
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current.scrollHeight,
    });
  }, [entries.length, busy, open]);

  const close = () => {
    setOpen(false);
    toggleRef.current?.focus();
  };

  const ask = (text: string) => {
    if (!text.trim() || busy) return;
    send.mutate({ chatId, text: text.trim() });
    setDraft("");
  };

  return (
    <div
      onKeyDown={(event) => open && event.key === "Escape" && close()}
      className="fixed right-7 bottom-7 z-30 flex flex-col items-end gap-3"
    >
      {open && (
        <section
          id={panelId}
          aria-label={t("assistant.title")}
          className="bg-panel border-hair shadow-float flex w-[360px] max-w-[calc(100vw-56px)] flex-col rounded-2xl border"
        >
          <div className="border-hair-soft flex flex-col gap-0.5 border-b px-[18px] py-4">
            <span className="flex items-center gap-2 font-semibold">
              <span className="text-amber flex">
                <Sparkle size={16} />
              </span>
              {t("assistant.title")}
              {entries.length > 0 && (
                <button
                  type="button"
                  onClick={newChat}
                  disabled={busy}
                  aria-label={t("assistant.newChat")}
                  title={t("assistant.newChat")}
                  className="text-ink-3 hover:text-ink ml-auto flex cursor-pointer rounded-md border-0 bg-transparent p-1 disabled:opacity-60"
                >
                  <SquarePen size={16} />
                </button>
              )}
            </span>
            <span className="text-ink-3 text-[13px]">
              {topic
                ? t("assistant.askAbout", {
                    topic: topic.toLocaleLowerCase(i18n.language),
                  })
                : t("assistant.askAnything")}
            </span>
          </div>
          {entries.length === 0 && !busy ? (
            <div className="flex flex-col gap-2 px-[18px] py-4">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => ask(suggestion)}
                  className="border-hair text-ink-2 min-h-9 cursor-pointer rounded-[10px] border bg-transparent px-3 py-2 text-left text-[13px]"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          ) : (
            <ol
              ref={transcriptRef}
              aria-label={t("assistant.conversation")}
              aria-live="polite"
              className="m-0 flex max-h-[min(420px,50vh)] list-none flex-col gap-3 overflow-y-auto px-[18px] py-4"
            >
              {entries.map((entry, index) => (
                <li key={index} className="flex flex-col">
                  {entry.role === "user" ? (
                    <p className="bg-chip text-ink m-0 max-w-[85%] self-end rounded-xl px-3 py-2 text-sm whitespace-pre-wrap">
                      {entry.text}
                    </p>
                  ) : entry.reply.status === "completed" ? (
                    <p className="text-ink m-0 max-w-[85%] text-sm whitespace-pre-wrap">
                      {entry.reply.reply}
                    </p>
                  ) : entry.reply.status === "input_required" ? (
                    <ChatWidget
                      taskId={entry.reply.task_id}
                      widget={entry.reply.widget}
                      live={index === entries.length - 1}
                    />
                  ) : (
                    <p className="text-crit m-0 text-[13px]">
                      {t("assistant.failed", { reason: entry.reply.reason })}
                    </p>
                  )}
                </li>
              ))}
              {busy && (
                <li role="status" className="text-ink-3 text-[13px]">
                  {t("assistant.thinking")}
                </li>
              )}
            </ol>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              ask(draft);
            }}
            className="flex items-end gap-2 px-[18px] pb-[18px]"
          >
            <label className="flex flex-1">
              <span className="sr-only">{t("assistant.message")}</span>
              <textarea
                rows={2}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    ask(draft);
                  }
                }}
                placeholder={t("assistant.placeholder")}
                className="border-hair bg-ground text-ink min-h-10 flex-1 resize-none rounded-lg border px-3 py-2 text-sm leading-normal"
              />
            </label>
            <button
              type="submit"
              disabled={busy || !draft.trim()}
              className={buttonClass("primary")}
            >
              {t("assistant.send")}
            </button>
          </form>
        </section>
      )}
      <button
        ref={toggleRef}
        type="button"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen(!open)}
        className="bg-primary text-on-primary flex min-h-[52px] cursor-pointer items-center gap-2.5 rounded-full pr-5 pl-4 font-semibold shadow-[0_8px_24px_rgb(28_25_23/0.22)]"
      >
        <span className="text-amber-soft flex">
          <Sparkle size={20} />
        </span>
        {t(open ? "assistant.close" : "assistant.open")}
      </button>
    </div>
  );
}
