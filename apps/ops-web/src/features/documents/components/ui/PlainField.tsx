import { useEffect, useLayoutEffect, useRef } from "react";
import { isPending } from "../../lib/changes";
import { useEditorStore } from "../../state/editorStore";
import { REWORDED } from "./chrome";
import { usePage } from "./PageContext";

const textOf = (element: HTMLElement) =>
  (element.textContent ?? "").replace(/\s+/g, " ").trim();

export default function PlainField({
  path,
  text,
  item,
}: {
  path: string;
  text: string;
  item?: string;
}) {
  const page = usePage();
  const ref = useRef<HTMLSpanElement>(null);
  const focus = useEditorStore((state) => state.focus === path);
  const { focusNext } = useEditorStore.getState();
  const removed = useRef(false);
  const remove = () => {
    removed.current = true;
    page.edit([{ kind: "delete", path: item! }]);
  };

  useLayoutEffect(() => {
    if (ref.current && document.activeElement !== ref.current)
      ref.current.textContent = text;
  }, [text]);

  useEffect(() => {
    if (!focus || !ref.current) return;
    ref.current.focus();
    window.getSelection()?.selectAllChildren(ref.current);
    focusNext(null);
  }, [focus, focusNext]);

  return (
    <span
      ref={ref}
      contentEditable="plaintext-only"
      suppressContentEditableWarning
      spellCheck={false}
      data-path={path}
      className="cursor-text"
      style={{
        background: isPending(page.pending, path) ? REWORDED : undefined,
      }}
      onClick={(event) => event.preventDefault()}
      onKeyDown={(event) => {
        if (item && event.key === "Backspace" && !textOf(event.currentTarget)) {
          event.preventDefault();
          const fields = [
            ...document.querySelectorAll<HTMLElement>("[data-path]"),
          ];
          const previous = fields
            .slice(0, fields.indexOf(event.currentTarget))
            .filter((field) => !field.dataset.path!.startsWith(`${item}/`))
            .at(-1);
          remove();
          if (!previous) return;
          previous.focus();
          window.getSelection()?.selectAllChildren(previous);
          window.getSelection()?.collapseToEnd();
          return;
        }
        if (event.key !== "Enter" && event.key !== "Escape") return;
        event.preventDefault();
        if (event.key === "Escape") event.currentTarget.textContent = text;
        event.currentTarget.blur();
      }}
      onBlur={(event) => {
        if (removed.current) return;
        const next = textOf(event.currentTarget);
        if (!next && item) return remove();
        if (!next) event.currentTarget.textContent = text;
        if (!next || next === text) return;
        page.edit([
          {
            kind: "update_field",
            path,
            value: { text: next, src: [page.source] },
          },
        ]);
      }}
    />
  );
}
