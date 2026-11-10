import type { Align } from "@renderverse/document-renderer";
import type { Editor } from "@tiptap/core";
import { useTranslation } from "react-i18next";
import { useEditorStore } from "../../state/editorStore";

interface Tool {
  name:
    | "bold"
    | "italic"
    | "underline"
    | "smaller"
    | "normal"
    | "larger"
    | "left"
    | "center"
    | "justify";
  glyph: string;
  className: string;
  run: (editor: Editor) => Align | undefined;
}

const TOOLS: Tool[] = [
  {
    name: "bold",
    glyph: "B",
    className: "text-sm font-bold",
    run: (editor) => void editor.chain().focus().toggleMark("bold").run(),
  },
  {
    name: "italic",
    glyph: "I",
    className: "font-[Georgia,serif] text-[15px] font-medium italic",
    run: (editor) => void editor.chain().focus().toggleMark("italic").run(),
  },
  {
    name: "underline",
    glyph: "U",
    className: "text-sm font-medium underline",
    run: (editor) => void editor.chain().focus().toggleMark("underline").run(),
  },
  {
    name: "smaller",
    glyph: "A",
    className: "ml-2 text-[11px] font-semibold",
    run: (editor) =>
      void editor.chain().focus().setMark("size", { size: "small" }).run(),
  },
  {
    name: "normal",
    glyph: "A",
    className: "text-sm font-semibold",
    run: (editor) => void editor.chain().focus().unsetMark("size").run(),
  },
  {
    name: "larger",
    glyph: "A",
    className: "text-[17px] font-semibold",
    run: (editor) =>
      void editor.chain().focus().setMark("size", { size: "large" }).run(),
  },
  {
    name: "left",
    glyph: "⇤",
    className: "ml-2 text-sm font-medium",
    run: () => "left",
  },
  {
    name: "center",
    glyph: "↔",
    className: "text-sm font-medium",
    run: () => "center",
  },
  {
    name: "justify",
    glyph: "≡",
    className: "text-[15px] font-medium",
    run: () => "justify",
  },
];

export default function FormatToolbar() {
  const { t } = useTranslation();
  const toolbar = useEditorStore((state) => state.toolbar);
  const formatting = useEditorStore((state) => state.formatting);
  if (!toolbar || !formatting) return null;

  return (
    <div
      role="toolbar"
      aria-label={t("documents.page.format.label")}
      className="absolute z-[8] flex -translate-x-1/2 gap-0.5 rounded-[10px] bg-[#1C1917] p-1 font-sans shadow-[0_8px_20px_rgba(28,25,23,0.28)]"
      style={{ left: toolbar.left, top: toolbar.top }}
    >
      {TOOLS.map((tool) => (
        <button
          key={tool.name}
          type="button"
          aria-label={t(`documents.page.format.${tool.name}`)}
          title={t(`documents.page.format.${tool.name}`)}
          onMouseDown={(event) => {
            event.preventDefault();
            formatting.commit(tool.run(formatting.editor));
          }}
          className={`h-[30px] min-w-[30px] cursor-pointer rounded-md border-0 bg-transparent px-1.5 text-[#FAFAF9] ${tool.className}`}
        >
          {tool.glyph}
        </button>
      ))}
    </div>
  );
}
