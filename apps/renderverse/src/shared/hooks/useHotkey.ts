import { useEffect, useLayoutEffect, useRef } from "react";

const isTypingTarget = (el: EventTarget | null) =>
  el instanceof HTMLElement &&
  (el.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName));

export const useHotkey = (
  code: string,
  handler: (e: KeyboardEvent) => void,
  enabled = true,
) => {
  const handlerRef = useRef(handler);

  useLayoutEffect(() => {
    handlerRef.current = handler;
  });

  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (
        e.code !== code ||
        e.repeat ||
        e.ctrlKey ||
        e.metaKey ||
        e.altKey ||
        isTypingTarget(e.target)
      )
        return;
      handlerRef.current(e);
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [code, enabled]);
};
