import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Chat, Conversation } from "../api/assistant";
import {
  answerTaskMutationOptions,
  clearConversationMutationOptions,
  decideMutationOptions,
  documentsQueryOptions,
  followDocumentMutationOptions,
  followTurnMutationOptions,
  sendMessageMutationOptions,
  sessionQueryOptions,
  stopMutationOptions,
  threadMessagesQueryOptions,
} from "../queries/assistant";
import {
  historyEntry,
  openTurn,
  useAssistantStore,
  type ChatEntry,
} from "../state/assistantStore";

const NO_ENTRIES: ChatEntry[] = [];

export function useSendMessage() {
  return useMutation(sendMessageMutationOptions);
}

export function useAnswerTask() {
  return useMutation(answerTaskMutationOptions);
}

export function useDecide() {
  return useMutation(decideMutationOptions);
}

export function useStop() {
  return useMutation(stopMutationOptions);
}

export function useDocuments() {
  return useQuery(documentsQueryOptions);
}

export function useFollowDocument() {
  return useMutation(followDocumentMutationOptions);
}

export function useClearConversation() {
  return useMutation(clearConversationMutationOptions);
}

export function useConversation(conversation: Conversation) {
  const session = useQuery(sessionQueryOptions(conversation));
  const threadId = session.data?.thread_id;
  const history = useInfiniteQuery({
    ...threadMessagesQueryOptions({ threadId: threadId ?? "" }),
    enabled: threadId !== undefined,
  });
  const stored = useAssistantStore(
    (state) => (threadId && state.live[threadId]) || NO_ENTRIES,
  );
  const { mutate: follow } = useMutation(followTurnMutationOptions);
  const newest = history.data?.pages[0];
  const last = newest?.messages.at(-1);
  const live = useMemo(
    () => stored.filter((entry) => !newest?.covers.includes(entry)),
    [newest, stored],
  );
  const entries = useMemo(
    () => [
      ...[...(history.data?.pages ?? [])]
        .reverse()
        .flatMap((page) => page.messages.map(historyEntry)),
      ...live,
    ],
    [history.data, live],
  );

  useEffect(() => {
    if (threadId && last?.role === "user" && live.length === 0)
      follow({ threadId });
  }, [follow, last, live.length, threadId]);

  return {
    chat: threadId ? ({ threadId } satisfies Chat) : undefined,
    entries,
    running: openTurn(live),
    history,
    error: session.error ?? history.error,
  };
}

export function useOlderMessages(
  history: ReturnType<typeof useConversation>["history"],
) {
  const [sentinel, setSentinel] = useState<HTMLElement | null>(null);
  const anchor = useRef<{ element: Element; top: number } | null>(null);
  const { fetchNextPage, hasNextPage } = history;
  const pages = history.data?.pages.length ?? 0;

  useLayoutEffect(() => {
    const saved = anchor.current;
    if (!saved) return;
    anchor.current = null;
    const delta = saved.element.getBoundingClientRect().top - saved.top;
    let scroller = saved.element.parentElement;
    while (
      scroller &&
      !/auto|scroll/.test(getComputedStyle(scroller).overflowY)
    )
      scroller = scroller.parentElement;
    if (delta) (scroller ?? window).scrollBy(0, delta);
  }, [pages]);

  useEffect(() => {
    if (!sentinel || !hasNextPage) return;
    const observer = new IntersectionObserver(([seen]) => {
      if (!seen?.isIntersecting) return;
      const first = sentinel.nextElementSibling;
      if (first)
        anchor.current = {
          element: first,
          top: first.getBoundingClientRect().top,
        };
      void fetchNextPage({ cancelRefetch: false });
    });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, pages, sentinel]);

  return setSentinel;
}
