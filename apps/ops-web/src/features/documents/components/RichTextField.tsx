import { Mark } from "@tiptap/core";
import Bold from "@tiptap/extension-bold";
import Document from "@tiptap/extension-document";
import Italic from "@tiptap/extension-italic";
import Link from "@tiptap/extension-link";
import Paragraph from "@tiptap/extension-paragraph";
import Text from "@tiptap/extension-text";
import Underline from "@tiptap/extension-underline";
import { UndoRedo } from "@tiptap/extensions";
import { EditorContent, useEditor, useEditorState } from "@tiptap/react";
import {
  Bold as BoldIcon,
  Italic as ItalicIcon,
  Underline as UnderlineIcon,
} from "lucide-react";
import { useEffect, useId, useRef } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";

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

const MARKS = [
  { name: "bold", Icon: BoldIcon },
  { name: "italic", Icon: ItalicIcon },
  { name: "underline", Icon: UnderlineIcon },
] as const;

const inner = (html: string) => html.replace(/^<p>/, "").replace(/<\/p>$/, "");

export default function RichTextField({
  label,
  value,
  onSave,
}: {
  label: string;
  value: string;
  onSave: (html: string) => void;
}) {
  const { t } = useTranslation();
  const labelId = useId();
  const saved = useRef(value);
  const editor = useEditor({
    extensions: EXTENSIONS,
    content: value,
    editorProps: {
      attributes: {
        role: "textbox",
        "aria-labelledby": labelId,
        class:
          "border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 py-2 text-sm leading-normal outline-none [&_a]:underline",
      },
    },
    onCreate: ({ editor }) => {
      saved.current = inner(editor.getHTML());
    },
    onBlur: ({ editor }) => {
      const html = inner(editor.getHTML());
      if (html === saved.current) return;
      saved.current = html;
      onSave(html);
    },
  });
  const active = useEditorState({
    editor,
    selector: ({ editor }) =>
      Object.fromEntries(
        MARKS.map(({ name }) => [name, editor.isActive(name)]),
      ),
  });

  useEffect(() => {
    if (editor.isFocused) return;
    editor.commands.setContent(value, { emitUpdate: false });
    saved.current = inner(editor.getHTML());
  }, [editor, value]);

  return (
    <div className="text-ink-3 flex flex-col gap-1.5 text-sm">
      <span className="flex items-center justify-between gap-2">
        <span id={labelId}>{label}</span>
        <span className="flex gap-1">
          {MARKS.map(({ name, Icon }) => (
            <button
              key={name}
              type="button"
              aria-label={t(`documents.content.${name}`)}
              aria-pressed={active[name]}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => editor.chain().focus().toggleMark(name).run()}
              className={cn(
                "inline-flex size-7 cursor-pointer items-center justify-center rounded-md border-0",
                active[name]
                  ? "bg-well text-ink"
                  : "text-ink-3 hover:text-ink bg-transparent",
              )}
            >
              <Icon size={14} />
            </button>
          ))}
        </span>
      </span>
      <EditorContent editor={editor} />
    </div>
  );
}
