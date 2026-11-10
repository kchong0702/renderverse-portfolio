import {
  ArrowUp,
  Check,
  ChevronRight,
  CircleAlert,
  FileCheck,
  FileText,
  LoaderCircle,
  Pause,
  Sparkle,
  Square,
  SquarePen,
  X,
} from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import {
  MAX_RECONNECTS,
  type DocumentKind,
  type Step,
  type Widget,
} from "../api/assistant";
import {
  useAnswerTask,
  useChat,
  useDocuments,
  useResumeTurns,
  useSendMessage,
  useStop,
} from "../hooks/useAssistant";
import {
  openTurn,
  useAssistantStore,
  type AssistantTurn,
  type ChatEntry,
  type Part,
} from "../state/assistantStore";

const NO_ENTRIES: ChatEntry[] = [];

const fieldClass =
  "border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 py-2 text-sm leading-normal disabled:opacity-60";

function DocumentPills({
  kind,
  disabled,
  onPick,
}: {
  kind: DocumentKind | null;
  disabled: boolean;
  onPick: (title: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const documents = useDocuments();

  if (documents.isPending)
    return (
      <p role="status" className="text-ink-3 m-0 text-[13px]">
        {t("assistant.documents.loading")}
      </p>
    );
  if (documents.isError)
    return (
      <p role="alert" className="text-crit m-0 text-[13px]">
        {t("assistant.documents.failed", { reason: documents.error.message })}
      </p>
    );

  const choices = documents.data
    .filter((document) => !kind || document.kind === kind)
    .sort(
      (a, b) =>
        Number(b.master) - Number(a.master) ||
        a.title.localeCompare(b.title, i18n.language),
    );
  if (!choices.length)
    return (
      <p className="text-ink-3 m-0 text-[13px]">
        {t("assistant.documents.empty")}
      </p>
    );

  return (
    <ul
      aria-label={t("assistant.documents.label")}
      className="m-0 flex list-none flex-col gap-2 p-0"
    >
      {choices.map((document) => (
        <li key={document.id}>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onPick(document.title)}
            className="border-hair bg-panel text-ink hover:bg-chip flex min-h-12 w-full cursor-pointer items-center gap-2.5 rounded-xl border px-3.5 text-left text-sm disabled:cursor-default disabled:opacity-60"
          >
            <FileText size={16} className="text-ink-3 shrink-0" />
            <span className="flex-1 font-medium">{document.title}</span>
            {document.master && (
              <Badge>{t("assistant.documents.master")}</Badge>
            )}
          </button>
        </li>
      ))}
    </ul>
  );
}

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
  const chat = useChat();
  const [input, setInput] = useState("");
  const labelId = useId();
  const choosesDocument = widget.choose === "document";
  const asksInput = widget.input_placeholder !== null || choosesDocument;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        answer.mutate({
          chat,
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
      {live && choosesDocument && (
        <DocumentPills
          kind={widget.kind}
          disabled={answer.isPending}
          onPick={(title) =>
            answer.mutate({
              chat,
              taskId,
              answer: { input: title },
              shown: title,
            })
          }
        />
      )}
      {live && asksInput && (
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={
            widget.input_placeholder ?? t("assistant.documents.typeTitle")
          }
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
                  chat,
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

type Activity = Extract<Part, { kind: "thinking" | "step" }>;

type Labels = Partial<Record<string, string>>;

const stepIcons = {
  running: <LoaderCircle size={13} className="animate-spin" />,
  done: <Check size={13} className="text-ok" />,
  failed: <X size={13} className="text-crit" />,
  waiting: <Pause size={13} className="text-amber" />,
  stopped: <Square size={11} className="text-ink-3" />,
} satisfies Record<Step["status"] | "stopped", ReactNode>;

const isActivity = (part: Part): part is Activity =>
  part.kind === "thinking" || part.kind === "step";

function duration({ startedAt, endedAt }: AssistantTurn) {
  const seconds = Math.max(
    1,
    Math.round(((endedAt ?? startedAt) - startedAt) / 1000),
  );
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

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
        className="flex w-[13px] justify-center"
      >
        {stepIcons[status]}
      </span>
      {label}
    </span>
  );
}

function Timeline({
  activity,
  steps,
  substeps,
  ended,
}: {
  activity: Activity[];
  steps: Labels;
  substeps: Partial<Record<string, Labels>>;
  ended: boolean;
}) {
  return (
    <ol className="border-hair text-ink-3 m-0 ml-1.5 flex list-none flex-col gap-2 border-l py-0.5 pl-4 text-[13px]">
      {activity.map((part, index) => {
        if (part.kind === "thinking")
          return (
            <li key={index} className="whitespace-pre-wrap">
              {part.text}
            </li>
          );
        const label = steps[part.step.name];
        return (
          label && (
            <li key={part.step.id} className="flex flex-col gap-1">
              <span className="text-ink-2">
                <StepRow step={part.step} label={label} ended={ended} />
              </span>
              {part.substeps.map((substep) => {
                const sublabel = substeps[part.step.name]?.[substep.name];
                return (
                  sublabel && (
                    <span key={substep.id} className="pl-[21px]">
                      <StepRow step={substep} label={sublabel} ended={ended} />
                    </span>
                  )
                );
              })}
            </li>
          )
        );
      })}
    </ol>
  );
}

function Working({
  turn,
  steps,
  substeps,
}: {
  turn: AssistantTurn;
  steps: Labels;
  substeps: Partial<Record<string, Labels>>;
}) {
  const { t } = useTranslation();
  const shown = turn.parts.filter(
    (part): part is Extract<Part, { kind: "step" }> =>
      part.kind === "step" && Boolean(steps[part.step.name]),
  );
  const current = shown.filter((part) => part.step.status === "running").at(-1);
  const sub = current?.substeps
    .filter(
      (substep) =>
        substep.status === "running" &&
        substeps[current.step.name]?.[substep.name],
    )
    .at(-1);
  const thought = turn.parts.filter((part) => part.kind === "thinking").at(-1);
  const rows = shown.filter((part) => part !== current);

  return (
    <div className="flex flex-col gap-2">
      <p role="status" className="m-0 flex items-center gap-2 text-sm">
        <LoaderCircle size={14} className="text-ink-3 animate-spin" />
        <span className="shimmer font-medium">
          {current
            ? (steps[current.step.name] ?? t("assistant.thinking"))
            : t("assistant.thinking")}
        </span>
      </p>
      {(rows.length > 0 || current) && (
        <div className="border-hair text-ink-3 ml-1.5 flex flex-col gap-1.5 border-l pl-4 text-[13px]">
          {rows.map((part) => (
            <StepRow
              key={part.step.id}
              step={part.step}
              label={steps[part.step.name] ?? part.step.name}
              ended={false}
            />
          ))}
          {current?.substeps.map((substep) => {
            const label = substeps[current.step.name]?.[substep.name];
            return (
              label && (
                <span
                  key={substep.id}
                  className={substep === sub ? "text-ink-2" : undefined}
                >
                  <StepRow step={substep} label={label} ended={false} />
                </span>
              )
            );
          })}
        </div>
      )}
      {thought && (
        <p className="text-ink-3 m-0 line-clamp-2 text-[13px] italic">
          {thought.text.trim()}
        </p>
      )}
    </div>
  );
}

function Turn({
  turn,
  last,
  onRetry,
}: {
  turn: AssistantTurn;
  last: boolean;
  onRetry?: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const steps: Labels = t("assistant.steps", { returnObjects: true });
  const substeps: Partial<Record<string, Labels>> = t("assistant.substeps", {
    returnObjects: true,
  });
  const running = turn.outcome === null;
  const activity = turn.parts.filter(isActivity);
  const thoughtOrStep = activity.some((part) =>
    part.kind === "thinking"
      ? part.text.trim()
      : Boolean(steps[part.step.name]),
  );
  const timelineId = useId();

  return (
    <div className="flex flex-col gap-3">
      {running ? (
        <Working turn={turn} steps={steps} substeps={substeps} />
      ) : (
        thoughtOrStep && (
          <div className="flex flex-col gap-2">
            <button
              type="button"
              aria-expanded={open}
              aria-controls={timelineId}
              onClick={() => setOpen(!open)}
              className="text-ink-3 hover:text-ink-2 flex cursor-pointer items-center gap-1 self-start border-0 bg-transparent p-0 text-[13px] font-medium"
            >
              {t("assistant.thoughtFor", { duration: duration(turn) })}
              <ChevronRight
                size={14}
                className={
                  open
                    ? "rotate-90 transition-transform"
                    : "transition-transform"
                }
              />
            </button>
            {open && (
              <div id={timelineId}>
                <Timeline
                  activity={activity}
                  steps={steps}
                  substeps={substeps}
                  ended
                />
              </div>
            )}
          </div>
        )
      )}
      {turn.parts.map(
        (part, index) =>
          part.kind === "text" && (
            <p key={index} className="text-ink m-0 text-sm whitespace-pre-wrap">
              {part.text}
            </p>
          ),
      )}
      {turn.parts.map(
        (part, index) =>
          part.kind === "changeset" && (
            <div
              key={index}
              className="border-hair bg-well flex items-center gap-2.5 rounded-xl border px-3 py-2.5"
            >
              <FileCheck size={16} className="text-amber shrink-0" />
              <span className="flex flex-1 flex-col leading-tight">
                <span className="text-ink text-sm font-semibold">
                  {t("assistant.editsToReview", {
                    count: part.changeset.edits,
                  })}
                </span>
                <span className="text-ink-3 text-xs">
                  {part.changeset.title}
                </span>
              </span>
              <Link
                to={`/documents?doc=${part.changeset.document_id}&panel=changes`}
                className="bg-primary text-on-primary flex min-h-9 items-center rounded-full px-3.5 text-[13px] font-semibold no-underline"
              >
                {t("assistant.review")}
              </Link>
            </div>
          ),
      )}
      {running && turn.reconnecting > 0 && (
        <div role="status" className="flex flex-col gap-1 text-[13px]">
          <span className="text-ink-2 flex items-center gap-2">
            <LoaderCircle size={14} className="text-warn animate-spin" />
            {t("assistant.reconnecting", {
              attempt: turn.reconnecting,
              max: MAX_RECONNECTS,
            })}
          </span>
          <span className="text-ink-3">{t("assistant.keepsRunning")}</span>
        </div>
      )}
      {turn.outcome?.status === "input_required" ? (
        <ChatWidget
          taskId={turn.outcome.task_id}
          widget={turn.outcome.widget}
          live={last}
        />
      ) : turn.outcome?.status === "failed" ? (
        <div
          role="alert"
          className="bg-crit-bg flex items-start gap-2.5 rounded-xl px-3 py-2.5"
        >
          <CircleAlert size={15} className="text-crit mt-0.5 shrink-0" />
          <span className="flex flex-1 flex-col gap-2">
            <span className="text-ink text-[13px]">
              {t("assistant.failed", { reason: turn.outcome.reason })}
            </span>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="border-hair bg-panel text-ink min-h-8 cursor-pointer self-start rounded-full border px-3 text-[13px] font-semibold"
              >
                {t("assistant.tryAgain")}
              </button>
            )}
          </span>
        </div>
      ) : (
        turn.outcome?.status === "cancelled" && (
          <span className="border-hair text-ink-3 flex items-center gap-1.5 self-start rounded-full border px-2.5 py-0.5 text-xs font-medium">
            <Square size={9} className="fill-current" />
            {t("assistant.youStopped")}
          </span>
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
  const document = useAssistantStore((state) => state.document);
  const chat = useChat();
  const entries = useAssistantStore(
    (state) => state.chats[chat.kind][chat.id] ?? NO_ENTRIES,
  );
  const newChat = useAssistantStore((state) => state.newChat);
  const send = useSendMessage();
  const stop = useStop();
  useResumeTurns();
  const current = entries.at(-1);
  const running = openTurn(entries);
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
    if (!text.trim() || running) return;
    pinned.current = true;
    send.mutate({ chat, text: text.trim() });
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
              {!document && entries.length > 0 && (
                <button
                  type="button"
                  onClick={newChat}
                  disabled={running !== undefined}
                  aria-label={t("assistant.newChat")}
                  title={t("assistant.newChat")}
                  className="text-ink-3 hover:text-ink ml-auto flex cursor-pointer rounded-md border-0 bg-transparent p-1 disabled:opacity-60"
                >
                  <SquarePen size={16} />
                </button>
              )}
            </span>
            <span className="text-ink-3 text-[13px]">
              {document
                ? t("assistant.aboutDocument", { title: document.title })
                : topic
                  ? t("assistant.askAbout", {
                      topic: topic.toLocaleLowerCase(i18n.language),
                    })
                  : t("assistant.askAnything")}
            </span>
          </div>
          {entries.length === 0 ? (
            <div className="flex flex-col gap-2 px-[18px] py-4">
              {(document
                ? t("assistant.documentSuggestions", { returnObjects: true })
                : suggestions
              ).map((suggestion) => (
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
              aria-busy={running !== undefined}
              onScroll={(event) => {
                const { scrollHeight, scrollTop, clientHeight } =
                  event.currentTarget;
                pinned.current = scrollHeight - scrollTop - clientHeight < 32;
              }}
              className="m-0 flex max-h-[min(480px,55vh)] list-none flex-col gap-4 overflow-y-auto px-[18px] py-4"
            >
              {entries.map((entry, index) => (
                <li key={index} className="flex flex-col">
                  {entry.role === "user" ? (
                    <p className="bg-chip text-ink m-0 max-w-[85%] self-end rounded-2xl rounded-br-sm px-3.5 py-2 text-sm whitespace-pre-wrap">
                      {entry.text}
                    </p>
                  ) : (
                    <Turn
                      turn={entry}
                      last={entry === current}
                      onRetry={
                        entry === current && entries.at(-2)?.role === "user"
                          ? () => {
                              const asked = entries.at(-2);
                              if (asked?.role === "user") ask(asked.text);
                            }
                          : undefined
                      }
                    />
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
            className="border-hair-soft flex items-end gap-2 border-t p-3"
          >
            <label className="flex flex-1">
              <span className="sr-only">{t("assistant.message")}</span>
              <textarea
                rows={1}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    ask(draft);
                  }
                }}
                placeholder={
                  document
                    ? t("assistant.documentPlaceholder")
                    : t("assistant.placeholder")
                }
                className="border-hair bg-ground text-ink min-h-11 flex-1 resize-none rounded-[22px] border px-4 py-2.5 text-sm leading-normal"
              />
            </label>
            {running ? (
              <button
                type="button"
                aria-label={t("assistant.stop")}
                title={t("assistant.stop")}
                disabled={stop.isPending || !running.taskId}
                onClick={() =>
                  running.taskId &&
                  stop.mutate({ chat, taskId: running.taskId })
                }
                className="bg-primary text-on-primary flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full border-0 disabled:opacity-60"
              >
                <Square size={14} className="fill-current" />
              </button>
            ) : (
              <button
                type="submit"
                aria-label={t("assistant.send")}
                title={t("assistant.send")}
                disabled={!draft.trim()}
                className="bg-primary text-on-primary flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full border-0 disabled:cursor-default disabled:opacity-40"
              >
                <ArrowUp size={18} />
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
