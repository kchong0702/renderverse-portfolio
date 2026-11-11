import type { RichValue } from "@renderverse/document-renderer";
import { Mark } from "@tiptap/core";
import Bold from "@tiptap/extension-bold";
import Document from "@tiptap/extension-document";
import Italic from "@tiptap/extension-italic";
import Link from "@tiptap/extension-link";
import Paragraph from "@tiptap/extension-paragraph";
import Text from "@tiptap/extension-text";
import Underline from "@tiptap/extension-underline";
import { UndoRedo } from "@tiptap/extensions";
import { EditorContent, useEditor } from "@tiptap/react";
import { useEffect, useRef } from "react";
import { isPending } from "../lib/changes";
import { useEditorStore } from "../state/editorStore";
import { REWORDED } from "./ui/chrome";
import { usePage } from "./ui/PageContext";

const Size = Mark.create({
  name: "size",
  addAttributes() {
    return {
      size: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-size"),
        renderHTML: ({ size }) => ({ "data-size": size }),
      },
    };
  },
  parseHTML() {
    return [{ tag: "span[data-size]" }];
  },
  renderHTML({ HTMLAttributes }) {
    return ["span", HTMLAttributes, 0];
  },
});

const EXTENSIONS = [
  Document.extend({ content: "paragraph" }),
  Paragraph,
  Text,
  Bold.extend({ renderHTML: ({ HTMLAttributes }) => ["b", HTMLAttributes, 0] }),
  Italic.extend({
    renderHTML: ({ HTMLAttributes }) => ["i", HTMLAttributes, 0],
  }),
  Underline,
  Link.configure({
    openOnClick: false,
    autolink: false,
    HTMLAttributes: { rel: null, target: null, class: null },
  }),
  Size,
  UndoRedo,
];

const inner = (html: string) => html.replace(/^<p>/, "").replace(/<\/p>$/, "");

export default function RichTextField({
  path,
  value,
  className,
  onSplit,
  onRemove,
}: {
  path: string;
  value: RichValue;
  className?: string;
  onSplit?: (html: string) => void;
  onRemove?: (refocus: boolean) => void;
}) {
  const page = usePage();
  const focus = useEditorStore((state) => state.focus === path);
  const { setFormatting, focusNext } = useEditorStore.getState();
  const saved = useRef({ html: value.html, align: value.align ?? null });
  const removed = useRef(false);
  const editor = useEditor({
    extensions: EXTENSIONS,
    content: value.html,
    editorProps: {
      attributes: {
        "data-rich": "",
        "data-path": path,
        class: className ?? "",
      },
    },
    onCreate: ({ editor }) => {
      saved.current = { ...saved.current, html: inner(editor.getHTML()) };
    },
  });

  const commit = (align = saved.current.align) => {
    const html = inner(editor.getHTML());
    if (html === saved.current.html && align === saved.current.align) return;
    saved.current = { html, align };
    page.edit([
      {
        kind: "update_field",
        path,
        value: { html, align, src: [page.source] },
      },
    ]);
  };

  useEffect(() => {
    if (editor.isFocused) return;
    editor.commands.setContent(value.html, { emitUpdate: false });
    saved.current = {
      html: inner(editor.getHTML()),
      align: value.align ?? null,
    };
  }, [editor, value.html, value.align]);

  useEffect(() => {
    if (!focus) return;
    editor.commands.focus("end");
    focusNext(null);
  }, [editor, focus, focusNext]);

  return (
    <EditorContent
      editor={editor}
      onFocus={() => setFormatting({ editor, path, commit })}
      onBlur={() => {
        if (useEditorStore.getState().formatting?.path === path)
          setFormatting(null);
        if (removed.current) return;
        if (onRemove && editor.isEmpty) {
          removed.current = true;
          onRemove(false);
        } else commit();
      }}
      onKeyDownCapture={(event) => {
        const handled =
          (event.key === "Enter" && !event.shiftKey && onSplit) ||
          (event.key === "Backspace" && editor.isEmpty && onRemove) ||
          event.key === "Escape";
        if (!handled) return;
        event.preventDefault();
        event.stopPropagation();
        if (event.key === "Escape") {
          editor.commands.setContent(value.html, { emitUpdate: false });
          editor.commands.blur();
        } else if (event.key === "Enter") {
          saved.current = { ...saved.current, html: inner(editor.getHTML()) };
          onSplit?.(saved.current.html);
        } else {
          removed.current = true;
          onRemove?.(true);
        }
      }}
      style={{
        minHeight: "1.2em",
        padding: "0 2px",
        margin: "0 -2px",
        borderRadius: 2,
        textAlign: value.align ?? undefined,
        background: isPending(page.pending, path) ? REWORDED : undefined,
      }}
    />
  );
}
