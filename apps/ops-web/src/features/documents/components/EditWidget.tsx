import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import type { Answer, Widget } from "../api/documents";

const fieldClass =
  "border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 py-2 text-sm leading-normal disabled:opacity-60";

export default function EditWidget({
  widget,
  pending,
  onAnswer,
}: {
  widget: Widget;
  pending: boolean;
  onAnswer: (answer: Answer) => void;
}) {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const labelId = useId();
  const asksInput = widget.input_placeholder !== null;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onAnswer({ input: input.trim() || undefined, accept: true });
      }}
      className="border-hair flex flex-col gap-2 rounded-xl border p-3"
    >
      {widget.label && (
        <p id={labelId} className="text-ink m-0 text-sm">
          {widget.label}
        </p>
      )}
      {widget.input_value !== null && (
        <input
          disabled
          value={widget.input_value}
          aria-labelledby={labelId}
          className={fieldClass}
        />
      )}
      {asksInput && (
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={widget.input_placeholder ?? undefined}
          aria-labelledby={labelId}
          disabled={pending}
          className={fieldClass}
        />
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={pending || (asksInput && !input.trim())}
          className={buttonClass("primary")}
        >
          {widget.submit_btn ?? t("documents.request.send")}
        </button>
        {widget.cancel_btn !== null && (
          <button
            type="button"
            disabled={pending}
            onClick={() => onAnswer({ accept: false })}
            className={buttonClass()}
          >
            {widget.cancel_btn}
          </button>
        )}
      </div>
    </form>
  );
}
