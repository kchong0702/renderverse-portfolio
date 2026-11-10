import { Sparkle } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  openTurn,
  useAnswerTask,
  useAssistantStore,
  useResumeTurns,
  useSendMessage,
  useStop,
  type AssistantTurn,
  type ChatEntry,
} from "@/features/assistant";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import type { ChangesetRecord, DocumentRecord } from "../api/documents";
import {
  useDecideChangeset,
  usePendingChangeset,
  useUndoEdit,
} from "../hooks/useDocuments";
import { changedText } from "../lib/changes";
import { sourceName } from "../lib/sources";

const NO_ENTRIES: ChatEntry[] = [];

const chipClass =
  "border-hair text-ink-2 min-h-8 cursor-pointer rounded-full border bg-transparent px-3 text-[13px]";

function ChangeList({
  document,
  pending,
}: {
  document: DocumentRecord;
  pending: ChangesetRecord;
}) {
  const { t } = useTranslation();
  const undo = useUndoEdit();

  return (
    <div className="border-hair overflow-hidden rounded-xl border">
      {pending.changeset.edits.map((edit, index) => {
        const changed = changedText(edit);
        const origin = changed?.src[0];
        return (
          <div
            key={`${pending.id}-${index}`}
            className="border-hair-soft flex items-start gap-3 border-b px-3.5 py-3"
          >
            <span className="flex min-w-0 flex-1 flex-col gap-[3px]">
              <span className="font-medium">
                {changed?.text ?? t(`documents.assistant.changes.${edit.kind}`)}
              </span>
              <span className="text-ink-3 text-xs">
                {t("documents.assistant.from", {
                  source: origin
                    ? sourceName(t, origin, document.lines)
                    : t("documents.sources.agent"),
                })}
              </span>
            </span>
            <button
              type="button"
              disabled={undo.isPending}
              onClick={() =>
                undo.mutate({
                  id: document.id,
                  changesetId: pending.id,
                  index,
                })
              }
              className="text-amber min-h-8 cursor-pointer border-0 bg-transparent text-[13px] font-semibold"
            >
              {t("documents.assistant.undo")}
            </button>
          </div>
        );
      })}
      {undo.error && (
        <p role="alert" className="text-crit m-0 px-3.5 py-3 text-sm">
          {t("documents.assistant.undoFailed", { reason: undo.error.message })}
        </p>
      )}
    </div>
  );
}

function Turn({
  turn,
  document,
  changes,
}: {
  turn: AssistantTurn;
  document: DocumentRecord;
  changes: boolean;
}) {
  const { t } = useTranslation();
  const answer = useAnswerTask();
  const pending = usePendingChangeset(document.id);
  const steps: Record<string, string> = t("assistant.steps", {
    returnObjects: true,
  });
  const step = [...turn.parts].reverse().find((part) => part.kind === "step");
  const outcome = turn.outcome;

  return (
    <div className="flex flex-col gap-3">
      {!outcome && (
        <span className="shimmer text-[13px] font-medium">
          {(step?.kind === "step" && steps[step.step.name]) ||
            t("assistant.thinking")}
        </span>
      )}
      {turn.parts.map(
        (part, index) =>
          part.kind === "text" && (
            <p key={index} className="m-0 whitespace-pre-wrap">
              {part.text}
            </p>
          ),
      )}
      {changes && pending && (
        <ChangeList document={document} pending={pending} />
      )}
      {outcome?.status === "input_required" && (
        <div className="flex flex-col gap-2.5">
          {outcome.widget.label && (
            <p className="m-0">{outcome.widget.label}</p>
          )}
          <div className="flex flex-wrap gap-2">
            {[
              { label: outcome.widget.submit_btn, accept: true },
              { label: outcome.widget.cancel_btn, accept: false },
            ].map(
              ({ label, accept }) =>
                label && (
                  <button
                    key={label}
                    type="button"
                    disabled={answer.isPending}
                    onClick={() =>
                      answer.mutate({
                        chat: { kind: "document", id: document.id },
                        taskId: outcome.task_id,
                        answer: { accept },
                        shown: label,
                      })
                    }
                    className={cn(
                      "border-hair bg-panel inline-flex min-h-9 cursor-pointer items-center rounded-lg border px-4 text-sm font-semibold",
                      accept ? "text-ink" : "text-ink-3",
                    )}
                  >
                    {label}
                  </button>
                ),
            )}
          </div>
        </div>
      )}
      {outcome?.status === "failed" && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("assistant.failed", { reason: outcome.reason })}
        </p>
      )}
      {outcome?.status === "cancelled" && (
        <p className="text-ink-3 m-0 text-sm">{t("assistant.youStopped")}</p>
      )}
    </div>
  );
}

export default function AssistantPanel({
  document,
}: {
  document: DocumentRecord;
}) {
  const { t } = useTranslation();
  const chat = { kind: "document", id: document.id } as const;
  const entries = useAssistantStore(
    (state) => state.chats.document[document.id] ?? NO_ENTRIES,
  );
  const send = useSendMessage();
  const answer = useAnswerTask();
  const stop = useStop();
  const decide = useDecideChangeset();
  const pending = usePendingChangeset(document.id);
  const [draft, setDraft] = useState("");
  const inputId = useId();
  useResumeTurns();
  const running = openTurn(entries);
  const asking = entries.at(-1);
  const question =
    asking?.role === "assistant" &&
    asking.outcome?.status === "input_required" &&
    asking.outcome.widget.input_placeholder !== null
      ? asking.outcome
      : undefined;
  const changesTurn = entries
    .map(
      (entry) =>
        entry.role === "assistant" &&
        entry.parts.some((part) => part.kind === "changeset"),
    )
    .lastIndexOf(true);
  const ask = (text: string) => {
    if (!text.trim() || running) return;
    if (question)
      answer.mutate({
        chat,
        taskId: question.task_id,
        answer: { input: text.trim(), accept: true },
        shown: text.trim(),
      });
    else send.mutate({ chat, text: text.trim() });
    setDraft("");
  };

  return (
    <div className="flex flex-col">
      <div className="text-ink-3 flex items-center gap-2 px-5 pt-3.5 text-[13px]">
        <span className="text-amber flex">
          <Sparkle size={16} />
        </span>
        {t("assistant.aboutDocument", { title: document.title })}
      </div>
      <div
        role="log"
        aria-label={t("documents.assistant.conversation")}
        className="flex flex-col gap-[18px] p-5"
      >
        {pending && changesTurn < 0 && (
          <ChangeList document={document} pending={pending} />
        )}
        {entries.map((entry, index) =>
          entry.role === "user" ? (
            <div
              key={index}
              className="bg-chip max-w-[85%] self-end rounded-[14px_14px_4px_14px] px-3.5 py-2.5 whitespace-pre-wrap"
            >
              {entry.text}
            </div>
          ) : (
            <Turn
              key={index}
              turn={entry}
              document={document}
              changes={index === changesTurn}
            />
          ),
        )}
      </div>
      <div className="border-hair-soft mt-auto flex flex-col gap-3 border-t px-5 pt-4 pb-5">
        <div className="flex flex-wrap gap-2">
          {(
            t("documents.assistant.prompts", {
              returnObjects: true,
            }) as string[]
          ).map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={running !== undefined}
              onClick={() => ask(prompt)}
              className={chipClass}
            >
              {prompt}
            </button>
          ))}
        </div>
        {pending && (
          <div className="flex gap-2">
            {(["accepted", "rejected"] as const).map((status) => (
              <button
                key={status}
                type="button"
                disabled={decide.isPending}
                onClick={() =>
                  decide.mutate({
                    id: document.id,
                    changesetId: pending.id,
                    status,
                  })
                }
                className={cn(
                  buttonClass(status === "accepted" ? "primary" : "secondary"),
                  "flex-1",
                )}
              >
                {t(`documents.assistant.${status}`)}
              </button>
            ))}
          </div>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            ask(draft);
          }}
          className="flex items-end gap-2.5"
        >
          <label htmlFor={inputId} className="sr-only">
            {t("assistant.message")}
          </label>
          <textarea
            id={inputId}
            rows={2}
            value={draft}
            placeholder={
              question?.widget.input_placeholder ??
              t("documents.assistant.placeholder")
            }
            onChange={(event) => setDraft(event.target.value)}
            className="border-hair bg-ground text-ink min-h-10 flex-1 resize-y rounded-lg border px-3 py-2.5 text-sm leading-normal"
          />
          {running ? (
            <button
              type="button"
              disabled={stop.isPending || !running.taskId}
              onClick={() =>
                running.taskId && stop.mutate({ chat, taskId: running.taskId })
              }
              className={buttonClass()}
            >
              {t("assistant.stop")}
            </button>
          ) : (
            <button type="submit" className={buttonClass("primary")}>
              <Sparkle size={14} className="text-amber-soft" />
              {t("assistant.send")}
            </button>
          )}
        </form>
        {decide.error && (
          <p role="alert" className="text-crit m-0 text-sm">
            {t("documents.assistant.decideFailed", {
              reason: decide.error.message,
            })}
          </p>
        )}
      </div>
    </div>
  );
}
