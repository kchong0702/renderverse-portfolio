import type { ElementProps, EntryView } from "@renderverse/document-renderer";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import type { Edit } from "../../api/documents";
import {
  idToPlaceAfter,
  convertEntry,
  entryAt,
  newId,
  withNewIds,
  type EntryBlock,
} from "../../lib/items";
import { useEditorStore } from "../../state/editorStore";
import {
  dashedPillClass,
  dropLine,
  hoverOutline,
  toolbarClass,
  toolButtonClass,
  unzoom,
} from "./chrome";
import Handle from "./Handle";
import {
  DeleteIcon,
  DetailsIcon,
  DownIcon,
  DuplicateIcon,
  UpIcon,
} from "./Icons";
import { usePage } from "./PageContext";

export default function EntryFrame({
  block,
  entry,
  props: { children, ...props },
}: {
  block: EntryBlock;
  entry: EntryView;
  props: ElementProps;
}) {
  const { t } = useTranslation();
  const page = usePage();
  const path = `blocks/${block.id}/items/${entry.id}`;
  const key = `e:${path}`;
  const selected = useEditorStore((state) => state.selected === key);
  const hovered = useEditorStore((state) => state.hovered.entry === path);
  const drag = useEditorStore((state) => state.drag);
  const over = useEditorStore((state) => state.dropKey === key);
  const {
    select,
    enter,
    leave,
    startDrag,
    dropOver,
    endDrag,
    openDetails,
    closeDetails,
    clearSelection,
    focusNext,
  } = useEditorStore.getState();
  const items = block.items ?? [];
  const ids = items.map((item) => item.id);
  const index = ids.indexOf(entry.id);
  const item = items[index];
  const hot = hovered || selected;

  return (
    <article
      {...props}
      onMouseEnter={() => enter("entry", path)}
      onMouseLeave={() => leave("entry", path)}
      onDragOver={(event) => {
        if (drag?.kind !== "e") return;
        event.preventDefault();
        event.stopPropagation();
        dropOver(key);
      }}
      onDrop={(event) => {
        if (drag?.kind !== "e") return;
        event.preventDefault();
        event.stopPropagation();
        endDrag();
        const source = entryAt(page.record.body.content.blocks, drag.id);
        if (drag.id === path || !source?.item) return;
        const after = idToPlaceAfter(ids, source.item.id, entry.id);
        page.edit(
          source.block.id === block.id
            ? [{ kind: "move", path: drag.id, after }]
            : [
                { kind: "delete", path: drag.id },
                {
                  kind: "insert_item",
                  parent: `blocks/${block.id}/items`,
                  after,
                  item: convertEntry(
                    source.item,
                    source.block.kind,
                    block.kind,
                  ),
                },
              ],
        );
      }}
      style={{
        position: "relative",
        borderRadius: 3,
        outline: hoverOutline(selected, hovered && !drag),
        outlineOffset: "calc(3px * var(--unzoom))",
        boxShadow: over && drag?.id !== path ? dropLine : undefined,
      }}
    >
      <Handle
        icon={10}
        dot={2}
        aria-label={t("documents.page.select", { label: entry.title })}
        title={t("documents.page.dragTitle")}
        onClick={() => select(key)}
        onDragStart={(event) => {
          event.stopPropagation();
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", path);
          startDrag({ kind: "e", id: path });
        }}
        onDragEnd={endDrag}
        className={cn(
          "top-px left-[-16px] z-[3] h-[18px] w-3.5 rounded-[3px] text-[#78716C]",
          selected ? "bg-[#FDE68A]" : "bg-[#F5F5F4]",
          hot ? "opacity-100" : "opacity-0",
        )}
      />
      {selected && (
        <div
          role="toolbar"
          aria-label={t("documents.page.entryLabel", { label: entry.title })}
          className={cn(toolbarClass, "top-[-42px] left-0 items-center")}
        >
          <span className="text-ink-3 pr-2 pl-1.5 font-semibold">
            {t("documents.page.entry")}
          </span>
          <button
            type="button"
            aria-label={t("documents.page.moveUp")}
            title={t("documents.page.moveUp")}
            onClick={() =>
              index > 0 &&
              page.edit([{ kind: "move", path, after: ids[index - 2] ?? null }])
            }
            className={toolButtonClass}
          >
            <UpIcon />
          </button>
          <button
            type="button"
            aria-label={t("documents.page.moveDown")}
            title={t("documents.page.moveDown")}
            onClick={() =>
              index < ids.length - 1 &&
              page.edit([{ kind: "move", path, after: ids[index + 1] }])
            }
            className={toolButtonClass}
          >
            <DownIcon />
          </button>
          <button
            type="button"
            aria-label={t("documents.page.duplicate")}
            title={t("documents.page.duplicate")}
            onClick={() =>
              page.edit([
                {
                  kind: "insert_item",
                  parent: `blocks/${block.id}/items`,
                  after: entry.id,
                  item: withNewIds(item),
                },
              ])
            }
            className={toolButtonClass}
          >
            <DuplicateIcon />
          </button>
          <button
            type="button"
            aria-label={t("documents.page.deleteEntry")}
            title={t("documents.page.delete")}
            onClick={() => {
              clearSelection();
              if (useEditorStore.getState().details === path) closeDetails();
              page.edit([{ kind: "delete", path }]);
            }}
            className={cn(toolButtonClass, "text-crit")}
          >
            <DeleteIcon />
          </button>
          <button
            type="button"
            onClick={() => openDetails(path)}
            className={cn(toolButtonClass, "px-2 font-[inherit]")}
          >
            <DetailsIcon />
            {t("documents.page.details")}
          </button>
        </div>
      )}
      {children}
      {hot && (
        <button
          type="button"
          onClick={() => {
            const bullet = {
              id: newId(),
              text: { html: "", src: [page.source] },
            };
            const edit: Edit = {
              kind: "insert_item",
              parent: `${path}/bullets`,
              after: item.bullets?.at(-1)?.id ?? null,
              item: bullet,
            };
            focusNext(`${path}/bullets/${bullet.id}/text`);
            page.edit([edit]);
          }}
          className={`${dashedPillClass} ${unzoom} absolute top-full left-0 z-[4] mt-0.5 h-5 px-2`}
        >
          {t("documents.page.bullet")}
        </button>
      )}
    </article>
  );
}
