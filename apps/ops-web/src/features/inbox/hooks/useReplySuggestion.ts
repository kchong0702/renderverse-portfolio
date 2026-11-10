import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useApplications } from "@/features/applications";
import { useGoogleAccount } from "@/features/settings";
import { threadsOf } from "../lib/threads";
import { useInbox } from "./useInbox";

export function useReplySuggestion() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const { account } = useGoogleAccount();
  const inbox = useInbox(account !== null);
  const applications = useApplications();
  const threads = threadsOf(
    inbox.data?.messages ?? [],
    applications.data ?? [],
  );
  const open = params.get("thread") ?? threads[0]?.thread_id;
  const thread = threads.find(
    ({ state, thread_id }) => state === "needs_reply" && thread_id !== open,
  );
  if (!thread) return null;
  const company = thread.application?.company ?? thread.from_name;
  return {
    label: t("inbox.assistant.reply", { company }),
    text: t("inbox.assistant.replyMessage", {
      company,
      thread: thread.thread_id,
    }),
  };
}
