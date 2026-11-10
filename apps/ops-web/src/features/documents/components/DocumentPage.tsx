import {
  DocumentView,
  EditingContext,
  PAGE_MM,
  pageCss,
  templates,
  type Editing,
  type RichValue,
} from "@renderverse/document-renderer";
import "@renderverse/document-renderer/fonts.css";
import "@renderverse/document-renderer/styles.css";
import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import type { DocumentRecord, Edit } from "../api/documents";
import { arrangementOf } from "../lib/arrangement";
import { useEditorStore } from "../state/editorStore";
import AddSkill from "./ui/AddSkill";
import BlockFrame from "./ui/BlockFrame";
import BulletItem from "./ui/BulletItem";
import EntryFrame from "./ui/EntryFrame";
import FormatToolbar from "./ui/FormatToolbar";
import { PageContext } from "./ui/PageContext";
import PlainField from "./ui/PlainField";
import RegionFrame from "./ui/RegionFrame";
import RichTextField from "./RichTextField";

const PX_PER_MM = 96 / 25.4;

const RichField = (props: { path: string; value: RichValue }) => (
  <RichTextField {...props} className="dr-rich" />
);

const toolbarAt = (frame: HTMLElement) => {
  const selection = window.getSelection();
  const rich = selection?.anchorNode?.parentElement?.closest("[data-rich]");
  if (!selection || selection.isCollapsed || !rich) return null;
  const rect = selection.getRangeAt(0).getBoundingClientRect();
  const box = frame.getBoundingClientRect();
  return {
    left: rect.left + rect.width / 2 - box.left,
    top: rect.top - box.top - 46,
  };
};

const editing: Editing = {
  Region: RegionFrame,
  BlockRoot: BlockFrame,
  Entry: EntryFrame,
  Bullet: BulletItem,
  Text: PlainField,
  RichText: RichField,
  AddSkill,
};

export default function DocumentPage({
  record,
  source,
  pending,
  pages,
  onPages,
  onEdit,
}: {
  record: DocumentRecord;
  source: string;
  pending: string[];
  onEdit: (edits: Edit[]) => void;
  pages: number;
  onPages: (pages: number) => void;
}) {
  const { t } = useTranslation();
  const setToolbar = useEditorStore((state) => state.setToolbar);
  const well = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const [available, setAvailable] = useState(0);
  const design = record.body.design;
  const template = templates[design.template] ?? templates.classic;
  const [width, height] = PAGE_MM[design.page_size];
  const zoom = Math.min(available / (width * PX_PER_MM), 1);
  const perPage = (height - 2 * design.margins_mm) * PX_PER_MM;

  useLayoutEffect(() => {
    const content = frame.current!.querySelector<HTMLElement>(".dr-page")!;
    const observer = new ResizeObserver(() => {
      setAvailable(well.current!.clientWidth - 88);
      onPages(Math.max(1, Math.ceil(content.offsetHeight / perPage - 0.005)));
    });
    observer.observe(well.current!);
    observer.observe(content);
    return () => observer.disconnect();
  }, [onPages, perPage]);

  return (
    <div
      ref={well}
      className="bg-well flex justify-center rounded-[14px] px-11 py-10"
    >
      <div
        ref={frame}
        className="relative bg-white text-[#1C1917] shadow-[0_4px_18px_rgba(28,25,23,0.10)]"
        style={{ width: width * PX_PER_MM * zoom }}
        onMouseUp={() => setToolbar(toolbarAt(frame.current!))}
        onKeyUp={() => setToolbar(toolbarAt(frame.current!))}
      >
        <style>{pageCss(record.body, template)}</style>
        <div
          className="pagedjs_page"
          style={
            {
              zoom: zoom || 1,
              width: `${width}mm`,
              minHeight: `${height}mm`,
              padding: `${design.margins_mm}mm 0`,
              boxSizing: "border-box",
              "--unzoom": 1 / (zoom || 1),
            } as CSSProperties
          }
        >
          <PageContext.Provider
            value={{
              record,
              template,
              arrangement: arrangementOf(record.body, template),
              source,
              pending,
              edit: onEdit,
            }}
          >
            <EditingContext.Provider value={editing}>
              <DocumentView
                document={record.body}
                template={template}
                assetUrl={(hash) => record.body.assets?.[hash]?.uri ?? ""}
              />
            </EditingContext.Provider>
          </PageContext.Provider>
        </div>
        {Array.from({ length: pages - 1 }, (_, index) => (
          <div
            key={index}
            aria-hidden="true"
            className="pointer-events-none absolute right-[-12px] left-[-12px] border-t-2 border-dashed border-[#D97706]"
            style={{
              top: Math.round(
                (design.margins_mm * PX_PER_MM + (index + 1) * perPage) * zoom,
              ),
            }}
          >
            <span className="absolute top-[-22px] right-0 rounded-full bg-[#FFF7E6] px-2 py-px font-sans text-[11px] font-semibold text-[#A35400]">
              {t("documents.page.pageStarts", { page: index + 2 })}
            </span>
          </div>
        ))}
        <FormatToolbar />
      </div>
    </div>
  );
}
