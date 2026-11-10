import { useIsMutating } from "@tanstack/react-query";
import {
  CircleCheck,
  CirclePause,
  CircleStop,
  CircleX,
  LoaderCircle,
  Sparkle,
  SquarePen,
} from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import type { Step, Widget } from "../api/assistant";
import { useAnswerTask, useSendMessage, useStop } from "../hooks/useAssistant";
import { useAssistantStore, type AssistantTurn } from "../state/assistantStore";

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
      {live && answer.error && (
        <p role="alert" className="text-crit m-0 text-[13px]">
          {t("assistant.answerFailed", { reason: answer.error.message })}
        </p>
      )}
    </form>
  );
}

const stepIcons = {
  running: <LoaderCircle size={14} className="text-ink-3 animate-spin" />,
  done: <CircleCheck size={14} className="text-ok" />,
  failed: <CircleX size={14} className="text-crit" />,
  waiting: <CirclePause size={14} className="text-amber" />,
  stopped: <CircleStop size={14} className="text-ink-3" />,
} satisfies Record<Step["status"] | "stopped", ReactNode>;

function StepRow({
  step,
  label,
  ended,
}: {
  step: Step;
  label: string;
  ended: boolean;
}) {
  const { t } = useTranslation();
  const status = ended && step.status === "running" ? "stopped" : step.status;

  return (
    <span className="flex items-center gap-2">
      <span
        role="img"
        aria-label={t(`assistant.stepStatus.${status}`)}
        className="flex"
      >
        {stepIcons[status]}
      </span>
      {label}
    </span>
  );
}

function Turn({ turn, last }: { turn: AssistantTurn; last: boolean }) {
  const { t } = useTranslation();
  const tools: Partial<
    Record<string, { label: string; steps: Partial<Record<string, string>> }>
  > = t("assistant.tools", { returnObjects: true });
  const running = turn.outcome === null;
  const end = turn.parts.at(-1);

  return (
    <div className="flex flex-col gap-2">
      {turn.parts.map((part, index) =>
        part.kind === "thinking" ? (
          <details key={index} className="text-ink-3 text-[13px]">
            <summary className="cursor-pointer">
              {running && part === end
                ? t("assistant.thinking")
                : t("assistant.thought")}
            </summary>
            <p className="border-hair m-0 mt-1 border-l pl-3 whitespace-pre-wrap">
              {part.text}
            </p>
          </details>
        ) : part.kind === "text" ? (
          <p
            key={index}
            className="text-ink m-0 max-w-[85%] text-sm whitespace-pre-wrap"
          >
            {part.text}
          </p>
        ) : (
          <div
            key={index}
            className="text-ink-2 flex flex-col gap-1 text-[13px]"
          >
            <StepRow
              step={part.step}
              ended={!running}
              label={tools[part.step.name]?.label ?? part.step.name}
            />
            {part.substeps.map((substep) => {
              const label = tools[part.step.name]?.steps[substep.name];
              return (
                label && (
                  <span key={substep.id} className="text-ink-3 pl-[22px]">
                    <StepRow step={substep} label={label} ended={!running} />
                  </span>
                )
              );
            })}
          </div>
        ),
      )}
      {running &&
        (!end || (end.kind === "step" && end.step.status !== "running")) && (
          <p role="status" className="text-ink-3 m-0 text-[13px]">
            {t("assistant.thinking")}
          </p>
        )}
      {turn.outcome?.status === "input_required" ? (
        <ChatWidget
          taskId={turn.outcome.task_id}
          widget={turn.outcome.widget}
          live={last}
        />
      ) : turn.outcome?.status === "failed" ? (
        <p className="text-crit m-0 text-[13px]">
          {t("assistant.failed", { reason: turn.outcome.reason })}
        </p>
      ) : (
        turn.outcome?.status === "cancelled" && (
          <p className="text-ink-3 m-0 text-[13px]">{t("assistant.stopped")}</p>
        )
      )}
    </div>
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
  const stop = useStop();
  const current = entries.at(-1);
  const running = current?.role === "assistant" && current.outcome === null;
  const busy = useIsMutating({ mutationKey: ["assistant"] }) > 0;
  const [draft, setDraft] = useState("");
  const toggleRef = useRef<HTMLButtonElement>(null);
  const transcriptRef = useRef<HTMLOListElement>(null);
  const pinned = useRef(true);
  const panelId = useId();

  useEffect(() => {
    if (pinned.current)
      transcriptRef.current?.scrollTo({
        top: transcriptRef.current.scrollHeight,
      });
  }, [entries, open]);

  const close = () => {
    setOpen(false);
    toggleRef.current?.focus();
  };

  const ask = (text: string) => {
    if (!text.trim() || busy) return;
    pinned.current = true;
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
              aria-busy={running}
              onScroll={(event) => {
                const { scrollHeight, scrollTop, clientHeight } =
                  event.currentTarget;
                pinned.current = scrollHeight - scrollTop - clientHeight < 32;
              }}
              className="m-0 flex max-h-[min(420px,50vh)] list-none flex-col gap-3 overflow-y-auto px-[18px] py-4"
            >
              {entries.map((entry, index) => (
                <li key={index} className="flex flex-col">
                  {entry.role === "user" ? (
                    <p className="bg-chip text-ink m-0 max-w-[85%] self-end rounded-xl px-3 py-2 text-sm whitespace-pre-wrap">
                      {entry.text}
                    </p>
                  ) : (
                    <Turn turn={entry} last={entry === current} />
                  )}
                </li>
              ))}
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
            {running ? (
              <button
                type="button"
                disabled={stop.isPending}
                onClick={() => stop.mutate({ chatId, taskId: current.taskId })}
                className={buttonClass()}
              >
                {t("assistant.stop")}
              </button>
            ) : (
              <button
                type="submit"
                disabled={busy || !draft.trim()}
                className={buttonClass("primary")}
              >
                {t("assistant.send")}
              </button>
            )}
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
