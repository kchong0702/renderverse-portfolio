import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { GoogleNotice } from "@/features/settings";
import { ApiError } from "@/shared/api/http";
import { buttonClass } from "@/shared/components/button";
import { TextField } from "@/shared/components/fields";
import type { Email } from "../api/inbox";
import { useSendEmail } from "../hooks/useInbox";

export default function ComposeForm({
  initial,
  onClose,
}: {
  initial: Email;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const headingId = useId();
  const send = useSendEmail();
  const [email, setEmail] = useState(initial);
  const locked = send.isPending || send.isSuccess;

  return (
    <form
      aria-labelledby={headingId}
      onSubmit={(event) => {
        event.preventDefault();
        send.mutate(email);
      }}
      className="bg-panel border-hair shadow-card flex min-w-0 flex-[999_1_460px] flex-col gap-4 rounded-xl border px-[30px] py-[26px]"
    >
      <h2 id={headingId} className="m-0 text-[20px] font-semibold">
        {t("inbox.compose.title")}
      </h2>
      <TextField
        label={t("inbox.compose.to")}
        type="email"
        required
        value={email.to}
        disabled={locked}
        onChange={(event) => setEmail({ ...email, to: event.target.value })}
      />
      <TextField
        label={t("inbox.compose.subject")}
        required
        value={email.subject}
        disabled={locked}
        onChange={(event) =>
          setEmail({ ...email, subject: event.target.value })
        }
      />
      <label className="text-ink-3 flex flex-col gap-1.5 text-sm">
        {t("inbox.compose.body")}
        <textarea
          required
          rows={10}
          value={email.body}
          disabled={locked}
          onChange={(event) => setEmail({ ...email, body: event.target.value })}
          className="border-hair bg-ground text-ink rounded-lg border px-3 py-2 text-sm leading-normal disabled:opacity-60"
        />
      </label>
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
      {send.isSuccess && (
        <p role="status" className="text-ok m-0 text-[14px] font-semibold">
          {t("inbox.compose.sent")}
        </p>
      )}
      <div className="flex flex-wrap gap-2.5">
        {!send.isSuccess && (
          <button
            type="submit"
            className={buttonClass("primary")}
            disabled={send.isPending}
          >
            {t("inbox.compose.send")}
          </button>
        )}
        <button type="button" className={buttonClass()} onClick={onClose}>
          {t(send.isSuccess ? "inbox.compose.close" : "inbox.compose.cancel")}
        </button>
      </div>
    </form>
  );
}
