import {
  ArrowUp,
  Check,
  ChevronRight,
  CircleAlert,
  FileCheck,
  FileText,
  LoaderCircle,
  Sparkle,
  createLucideIcon,
  type LucideIcon,
} from "lucide-react";
import { Fragment, useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Badge from "@/shared/components/Badge";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import {
  MAX_RECONNECTS,
  type DocumentKind,
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

const StopSquare = createLucideIcon("StopSquare", [
  [
    "rect",
    {
      x: "5",
      y: "5",
      width: "14",
      height: "14",
      rx: "2",
      fill: "currentColor",
      stroke: "none",
      key: "0",
    },
  ],
]);

const SearchAction = createLucideIcon("SearchAction", [
  ["circle", { cx: "11", cy: "11", r: "7", key: "0" }],
  ["path", { d: "m20 20-3.5-3.5", key: "1" }],
]);

const EditAction = createLucideIcon("EditAction", [
  ["path", { d: "M12 20h9", key: "0" }],
  ["path", { d: "M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z", key: "1" }],
]);

const actionIcons: Partial<Record<string, LucideIcon>> = {
  find_documents: SearchAction,
  find_jobs: SearchAction,
  search_jobs: SearchAction,
  analyse_job: SearchAction,
  edit_document: EditAction,
  propose_changeset: EditAction,
  agent: EditAction,
};

function DocumentChoices({
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
    <div
      role="group"
      aria-label={t(`assistant.documents.groups.${kind ?? "all"}`)}
      className="flex flex-col gap-2"
    >
      {choices.map((document) => (
        <button
          key={document.id}
          type="button"
          disabled={disabled}
          onClick={() => onPick(document.title)}
          className="border-hair bg-panel text-ink flex min-h-12 cursor-pointer items-center gap-2.5 rounded-xl border px-3.5 text-left text-sm disabled:cursor-default disabled:opacity-60"
        >
          <FileText size={16} className="text-ink-3 shrink-0" />
          <span className="flex-1 font-medium">{document.title}</span>
          {document.master ? (
            <Badge tone="accent">{t("assistant.documents.master")}</Badge>
          ) : (
            <span className="text-ink-3 text-xs">
              {t("assistant.documents.edited", {
                date: new Intl.DateTimeFormat(i18n.language, {
                  day: "numeric",
                  month: "short",
                }).format(new Date(document.updated_at)),
              })}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

function ChatWidget({
  taskId,
  widget,
  live,
  answer,
}: {
  taskId: string;
  widget: Widget;
  live: boolean;
  answer: ReturnType<typeof useAnswerTask>;
}) {
  const { t } = useTranslation();
  const chat = useChat();
  const typed =
    widget.input_placeholder !== null || widget.choose === "document";

  return (
    <>
      {widget.label && <p className="text-ink m-0 text-sm">{widget.label}</p>}
      {live && widget.input_value !== null && (
        <input
          disabled
          value={widget.input_value}
          aria-label={widget.label ?? undefined}
          className="border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 py-2 text-sm disabled:opacity-60"
        />
      )}
      {live && widget.choose === "document" && (
        <DocumentChoices
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
      {live && !typed && (
        <span className="flex gap-2">
          <button
            type="button"
            disabled={answer.isPending}
            onClick={() =>
              answer.mutate({
                chat,
                taskId,
                answer: { accept: true },
                shown: widget.submit_btn ?? t("assistant.send"),
              })
            }
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
        </span>
      )}
      {live && answer.error && (
        <p role="alert" className="text-crit m-0 text-[13px]">
          {t("assistant.answerFailed", { reason: answer.error.message })}
        </p>
      )}
    </>
  );
}

type StepPart = Extract<Part, { kind: "step" }>;

type Activity = Extract<Part, { kind: "thinking" | "step" }>;

type Labels = Partial<Record<string, string>>;

function duration({ startedAt, endedAt }: AssistantTurn) {
  const seconds = Math.max(
    1,
    Math.round(((endedAt ?? startedAt) - startedAt) / 1000),
  );
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function Timeline({
  id,
  activity,
  done,
  doneSubsteps,
}: {
  id: string;
  activity: Activity[];
  done: Labels;
  doneSubsteps: Partial<Record<string, Labels>>;
}) {
  const { t } = useTranslation();

  return (
    <ol
      id={id}
      aria-label={t("assistant.whatItDid")}
      className="border-hair text-ink-3 m-0 -mt-1 ml-1.5 flex list-none flex-col gap-2.5 border-l p-0 pl-[15px] text-[13px]"
    >
      {activity.map((part, index) => {
        if (part.kind === "thinking")
          return (
            <li key={index} className="whitespace-pre-wrap">
              {part.text}
            </li>
          );
        const Icon = actionIcons[part.step.name] ?? FileText;
        const substeps = part.substeps.filter(
          (substep) =>
            substep.status === "done" &&
            doneSubsteps[part.step.name]?.[substep.name],
        );
        return (
          <li key={part.step.id} className="flex flex-col gap-1.5">
            <span className="text-ink-2 flex items-center gap-2">
              <span className="text-ink-3 flex">
                <Icon size={13} strokeWidth={2} />
              </span>
              {done[part.step.name]}
            </span>
            {substeps.length > 0 && (
              <span className="ml-[21px] flex flex-col gap-1">
                {substeps.map((substep) => (
                  <span key={substep.id}>
                    {doneSubsteps[part.step.name]?.[substep.name]}
                  </span>
                ))}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function Working({
  turn,
  steps,
  substeps,
  done,
  doneSubsteps,
}: {
  turn: AssistantTurn;
  steps: Labels;
  substeps: Partial<Record<string, Labels>>;
  done: Labels;
  doneSubsteps: Partial<Record<string, Labels>>;
}) {
  const { t } = useTranslation();
  const shown = turn.parts.filter(
    (part): part is StepPart =>
      part.kind === "step" && Boolean(steps[part.step.name]),
  );
  const current = shown.filter((part) => part.step.status === "running").at(-1);
  const rows = shown.filter((part) => part.step.status === "done");
  const currentSubsteps =
    current?.substeps.filter(
      (substep) =>
        (substep.status === "done" &&
          doneSubsteps[current.step.name]?.[substep.name]) ||
        (substep.status === "running" &&
          substeps[current.step.name]?.[substep.name]),
    ) ?? [];
  const thought = turn.parts.filter((part) => part.kind === "thinking").at(-1);

  return (
    <div className="flex flex-col gap-2.5">
      <p role="status" className="m-0 flex items-center gap-2 text-sm">
        <LoaderCircle size={14} className="text-ink-3 animate-spin" />
        <span className="shimmer font-medium">
          {current ? steps[current.step.name] : t("assistant.thinking")}
        </span>
      </p>
      {(rows.length > 0 || currentSubsteps.length > 0) && (
        <div className="border-hair text-ink-3 ml-1.5 flex flex-col gap-[7px] border-l pl-[15px] text-[13px]">
          {rows.map((part) => (
            <span key={part.step.id} className="flex items-center gap-2">
              <Check size={13} strokeWidth={2.4} className="text-ok" />
              {done[part.step.name]}
            </span>
          ))}
          {current &&
            currentSubsteps.map((substep) =>
              substep.status === "done" ? (
                <span key={substep.id} className="flex items-center gap-2">
                  <Check size={13} strokeWidth={2.4} className="text-ok" />
                  {doneSubsteps[current.step.name]?.[substep.name]}
                </span>
              ) : (
                <span
                  key={substep.id}
                  className="text-ink-2 flex items-center gap-2"
                >
                  <LoaderCircle
                    size={13}
                    strokeWidth={2.4}
                    className="animate-spin"
                  />
                  {substeps[current.step.name]?.[substep.name]}
                </span>
              ),
            )}
        </div>
      )}
      {thought && (
        <p className="text-ink-3 m-0 mt-0.5 line-clamp-2 text-[13px] italic">
          {thought.text.trim()}
        </p>
      )}
    </div>
  );
}

function Turn({
  turn,
  last,
  answer,
  onRetry,
}: {
  turn: AssistantTurn;
  last: boolean;
  answer: ReturnType<typeof useAnswerTask>;
  onRetry?: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const steps: Labels = t("assistant.steps", { returnObjects: true });
  const substeps: Partial<Record<string, Labels>> = t("assistant.substeps", {
    returnObjects: true,
  });
  const changeset = turn.parts.find((part) => part.kind === "changeset");
  const done: Labels = {
    ...t("assistant.done", { returnObjects: true }),
    ...(changeset?.kind === "changeset" && {
      edit_document: t("assistant.edited", {
        title: changeset.changeset.title,
      }),
    }),
  };
  const doneSubsteps: Partial<Record<string, Labels>> = t(
    "assistant.doneSubsteps",
    { returnObjects: true },
  );
  const running = turn.outcome === null;
  const activity = turn.parts.filter(
    (part): part is Activity =>
      (part.kind === "thinking" && Boolean(part.text.trim())) ||
      (part.kind === "step" &&
        part.step.status === "done" &&
        Boolean(done[part.step.name])),
  );
  const timelineId = useId();

  return (
    <div className="flex flex-col gap-3.5">
      {running
        ? (turn.reconnecting === 0 || turn.parts.length > 0) && (
            <Working
              turn={turn}
              steps={steps}
              substeps={substeps}
              done={done}
              doneSubsteps={doneSubsteps}
            />
          )
        : activity.length > 0 && (
            <>
              <button
                type="button"
                aria-expanded={open}
                aria-controls={timelineId}
                onClick={() => setOpen(!open)}
                className="text-ink-3 flex cursor-pointer items-center gap-1.5 self-start border-0 bg-transparent px-0 py-1 text-[13px] font-medium"
              >
                {t("assistant.thoughtFor", { duration: duration(turn) })}
                <ChevronRight
                  size={14}
                  strokeWidth={2}
                  className={
                    open
                      ? "rotate-90 transition-transform"
                      : "transition-transform"
                  }
                />
              </button>
              {open && (
                <Timeline
                  id={timelineId}
                  activity={activity}
                  done={done}
                  doneSubsteps={doneSubsteps}
                />
              )}
            </>
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
        <div role="status" className="flex flex-col gap-3.5 text-[13px]">
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
          answer={answer}
        />
      ) : turn.outcome?.status === "failed" ? (
        <div
          role="alert"
          className="bg-crit-bg flex items-start gap-2.5 rounded-xl px-3 py-2.5"
        >
          <CircleAlert
            size={15}
            strokeWidth={2}
            className="text-crit mt-0.5 shrink-0"
          />
          <span className="flex flex-1 flex-col gap-2">
            <span className="text-ink text-[13px]">{turn.outcome.reason}</span>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="text-ink-3 min-h-8 cursor-pointer self-start rounded-full border-0 bg-transparent px-3 text-[13px] font-medium"
              >
                {t("assistant.tryAgain")}
              </button>
            )}
          </span>
        </div>
      ) : (
        turn.outcome?.status === "cancelled" && (
          <span className="border-hair text-ink-3 flex items-center gap-1.5 self-start rounded-full border px-2.5 py-0.5 text-xs font-medium">
            <StopSquare size={10} />
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
  const documentKind = useDocuments().data?.find(
    ({ id }) => id === document?.id,
  )?.kind;
  const send = useSendMessage();
  const answer = useAnswerTask();
  const stop = useStop();
  useResumeTurns();
  const current = entries.at(-1);
  const asked = entries.at(-2);
  const retryable =
    asked?.role === "user" && !asked.answered ? asked : undefined;
  const running = openTurn(entries);
  const outcome = current?.role === "assistant" ? current.outcome : null;
  const asking =
    outcome?.status === "input_required" &&
    (outcome.widget.input_placeholder !== null ||
      outcome.widget.choose === "document")
      ? outcome
      : undefined;
  const [draft, setDraft] = useState("");
  const toggleRef = useRef<HTMLButtonElement>(null);
  const transcriptRef = useRef<HTMLOListElement>(null);
  const pinned = useRef(true);
  const panelId = useId();
  const empty = entries.length === 0;
  const placeholder = asking
    ? (asking.widget.input_placeholder ?? t("assistant.documents.typeTitle"))
    : document
      ? t(`assistant.placeholders.${documentKind ?? "document"}`)
      : empty
        ? t("assistant.placeholder")
        : t("assistant.followUp");

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

  const submit = (text: string) => {
    if (!text.trim() || running || answer.isPending) return;
    pinned.current = true;
    if (asking)
      answer.mutate({
        chat,
        taskId: asking.task_id,
        answer: { input: text.trim(), accept: true },
        shown: text.trim(),
      });
    else send.mutate({ chat, text: text.trim() });
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
          className={cn(
            "bg-panel border-hair shadow-float flex w-[360px] max-w-[calc(100vw-56px)] flex-col rounded-2xl border",
            !empty && "h-[min(720px,calc(100vh-136px))] overflow-hidden",
          )}
        >
          {empty ? (
            <div className="border-hair-soft flex flex-col gap-0.5 border-b px-[18px] py-4">
              <span className="flex items-center gap-2 font-semibold">
                <span className="text-amber flex">
                  <Sparkle size={16} />
                </span>
                {t("assistant.title")}
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
          ) : (
            <header className="border-hair-soft flex items-center gap-2 border-b px-4 py-3.5">
              <span className="text-amber flex">
                <Sparkle size={16} />
              </span>
              <span className="flex-1 font-semibold">
                {t("assistant.title")}
              </span>
              <span className="text-ink-3 text-xs">
                {document?.title ?? topic}
              </span>
            </header>
          )}
          {empty ? (
            <div className="flex flex-col gap-2 px-[18px] py-4">
              {(document
                ? t("assistant.documentSuggestions", { returnObjects: true })
                : suggestions
              ).map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => submit(suggestion)}
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
              className="m-0 flex min-h-0 flex-1 list-none flex-col gap-3.5 overflow-y-auto px-4 py-[18px]"
            >
              {entries.map((entry, index) => (
                <Fragment key={index}>
                  {entry.role === "user" && index > 0 && !entry.answered && (
                    <li
                      role="presentation"
                      className="bg-hair-soft my-1 h-px shrink-0"
                    />
                  )}
                  <li className="flex flex-col">
                    {entry.role === "user" ? (
                      <p className="bg-bubble text-ink m-0 max-w-[85%] self-end rounded-2xl rounded-br-[4px] px-[13px] py-[9px] text-sm whitespace-pre-wrap">
                        {entry.text}
                      </p>
                    ) : (
                      <Turn
                        turn={entry}
                        last={entry === current}
                        answer={answer}
                        onRetry={
                          entry === current && retryable?.role === "user"
                            ? () => submit(retryable.text)
                            : undefined
                        }
                      />
                    )}
                  </li>
                </Fragment>
              ))}
            </ol>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              submit(draft);
            }}
            className={
              empty
                ? "flex items-end gap-2 px-[18px] pb-[18px]"
                : "border-hair-soft flex items-end gap-2 border-t p-3"
            }
          >
            <label className="flex flex-1">
              <span className="sr-only">
                {asking ? placeholder : t("assistant.message")}
              </span>
              <textarea
                rows={empty ? 2 : 1}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submit(draft);
                  }
                }}
                placeholder={placeholder}
                className={
                  empty
                    ? "border-hair bg-ground text-ink min-h-10 flex-1 resize-none rounded-lg border px-3 py-2 text-sm leading-normal"
                    : "border-hair bg-ground text-ink min-h-11 flex-1 resize-none rounded-[22px] border px-4 py-[11px] text-sm leading-normal"
                }
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
                <StopSquare size={14} />
              </button>
            ) : empty ? (
              <button
                type="submit"
                disabled={!draft.trim()}
                className={buttonClass("primary")}
              >
                {t("assistant.send")}
              </button>
            ) : (
              <button
                type="submit"
                aria-label={t("assistant.send")}
                title={t("assistant.send")}
                disabled={!draft.trim() || answer.isPending}
                className="bg-primary text-on-primary flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full border-0 disabled:cursor-default disabled:opacity-40"
              >
                <ArrowUp size={16} strokeWidth={2.2} />
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
