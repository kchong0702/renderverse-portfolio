import { Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import { TextAreaField } from "@/shared/components/fields";
import type { EditRun } from "../api/documents";
import { useAnswerEdit, useRequestEdit } from "../hooks/useDocuments";
import EditWidget from "./EditWidget";

export default function EditRequestForm({
  documentId,
}: {
  documentId: string;
}) {
  const { t } = useTranslation();
  const request = useRequestEdit();
  const answer = useAnswerEdit();
  const [text, setText] = useState("");
  const [run, setRun] = useState<{ requestId: string; result: EditRun }>();
  const pending = request.isPending || answer.isPending;
  const error = request.error ?? answer.error;
  const asked =
    run?.result.status === "input_required"
      ? { requestId: run.requestId, ...run.result }
      : undefined;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const requestId = crypto.randomUUID();
    setRun(undefined);
    answer.reset();
    request.mutate(
      { id: documentId, requestId, text: text.trim() },
      {
        onSuccess: (result) => {
          setRun({ requestId, result });
          if (result.status === "completed") setText("");
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={submit} className="flex flex-col gap-3">
        <TextAreaField
          label={t("documents.request.label")}
          placeholder={t("documents.request.placeholder")}
          value={text}
          maxLength={4000}
          disabled={pending}
          onChange={(event) => setText(event.target.value)}
        />
        <button
          type="submit"
          disabled={pending || !text.trim()}
          className={`${buttonClass("primary")} w-fit`}
        >
          <Sparkles size={16} className="text-amber-soft" />
          {request.isPending
            ? t("documents.request.asking")
            : t("documents.request.ask")}
        </button>
      </form>
      {pending ? (
        <p role="status" className="text-ink-3 m-0 text-sm">
          {t("documents.request.working")}
        </p>
      ) : error ? (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("documents.request.failed", { reason: error.message })}
        </p>
      ) : run?.result.status === "failed" ? (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("documents.request.failed", { reason: run.result.reason })}
        </p>
      ) : (
        run?.result.status === "completed" && (
          <p role="status" className="text-ink-3 m-0 text-sm">
            {t("documents.request.proposed", {
              count: run.result.reply.changeset.edits.length,
            })}
          </p>
        )
      )}
      {asked && (
        <EditWidget
          key={asked.task_id}
          widget={asked.widget}
          pending={pending}
          onAnswer={(reply) =>
            answer.mutate(
              {
                id: documentId,
                requestId: asked.requestId,
                taskId: asked.task_id,
                answer: reply,
              },
              {
                onSuccess: (result) => {
                  setRun({ requestId: asked.requestId, result });
                  if (result.status === "completed") setText("");
                },
              },
            )
          }
        />
      )}
    </div>
  );
}
