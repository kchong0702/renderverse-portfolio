import { useEffect, useLayoutEffect, useRef } from "react";
import { useEditorStore } from "../../state/editorStore";
import { usePage } from "./PageContext";

const textOf = (element: HTMLElement) =>
  (element.textContent ?? "").replace(/\s+/g, " ").trim();

export default function PlainField({
  path,
  text,
}: {
  path: string;
  text: string;
}) {
  const page = usePage();
  const ref = useRef<HTMLSpanElement>(null);
  const focus = useEditorStore((state) => state.focus === path);
  const { focusNext } = useEditorStore.getState();

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
      onClick={(event) => event.preventDefault()}
      onKeyDown={(event) => {
        if (event.key !== "Enter" && event.key !== "Escape") return;
        event.preventDefault();
        if (event.key === "Escape") event.currentTarget.textContent = text;
        event.currentTarget.blur();
      }}
      onBlur={(event) => {
        const next = textOf(event.currentTarget);
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
