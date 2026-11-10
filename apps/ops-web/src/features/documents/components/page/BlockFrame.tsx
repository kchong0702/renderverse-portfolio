import type {
  AnyBlock,
  BlockTag,
  ElementProps,
} from "@renderverse/document-renderer";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import {
  regionOf,
  relocate,
  savedFor,
  withBlockAfter,
  withoutBlock,
} from "../../lib/arrangement";
import { isSection, withNewIds } from "../../lib/items";
import { useEditorStore } from "../../state/editorStore";
import {
  dropLine,
  hoverOutline,
  toolbarClass,
  toolButtonClass,
} from "./chrome";
import Handle from "./Handle";
import HotBar from "./HotBar";
import { DeleteIcon, DownIcon, DuplicateIcon, MoveIcon, UpIcon } from "./icons";
import { arrange, blockLabel, usePage } from "./PageContext";

export default function BlockFrame({
  as: Tag,
  block,
  props: { children, ...props },
}: {
  as: BlockTag;
  block: AnyBlock;
  props: ElementProps;
}) {
  const { t } = useTranslation();
  const page = usePage();
  const key = `k:${block.id}`;
  const selected = useEditorStore((state) => state.selected === key);
  const hovered = useEditorStore((state) => state.hovered.block === block.id);
  const drag = useEditorStore((state) => state.drag);
  const over = useEditorStore((state) => state.dropKey === key);
  const moving = useEditorStore((state) => state.moving === block.id);
  const {
    select,
    enter,
    leave,
    startDrag,
    dropOver,
    endDrag,
    toggleMoving,
    clearSelection,
  } = useEditorStore.getState();
  const label = blockLabel(block, t);
  const design = page.record.body.design;
  const current = regionOf(page.arrangement, block.id);
  const section = isSection(block);

  const move = (offset: number) =>
    arrange(
      page,
      relocate(
        page.arrangement,
        block.id,
        current.region,
        () => current.blocks.indexOf(block.id) + offset,
      ),
    );

  return (
    <Tag
      {...props}
      onMouseEnter={() => enter("block", block.id)}
      onMouseLeave={() => leave("block", block.id)}
      onDragOver={(event) => {
        if (drag?.kind !== "k") return;
        event.preventDefault();
        event.stopPropagation();
        dropOver(key);
      }}
      onDrop={(event) => {
        if (drag?.kind !== "k") return;
        event.preventDefault();
        event.stopPropagation();
        endDrag();
        if (drag.id === block.id) return;
        const from = regionOf(page.arrangement, drag.id);
        const after =
          from.region === current.region &&
          from.blocks.indexOf(drag.id) < current.blocks.indexOf(block.id);
        arrange(
          page,
          relocate(
            page.arrangement,
            drag.id,
            current.region,
            (blocks) => blocks.indexOf(block.id) + (after ? 1 : 0),
          ),
        );
      }}
      style={{
        position: "relative",
        borderRadius: 3,
        outline: hoverOutline(selected, hovered && !drag),
        outlineOffset: "calc(4px * var(--unzoom))",
        boxShadow: over && drag?.id !== block.id ? dropLine : undefined,
      }}
    >
      <Handle
        icon={12}
        dot={1.7}
        aria-label={t("documents.page.select", { label })}
        title={t("documents.page.dragTitle")}
        onClick={() => select(key)}
        onDragStart={(event) => {
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", block.id);
          startDrag({ kind: "k", id: block.id });
        }}
        onDragEnd={endDrag}
        className={cn(
          "top-0 left-[-28px] z-[3] h-[22px] w-5 rounded text-[#78716C]",
          selected ? "bg-[#FDE68A]" : "bg-[#F5F5F4]",
          hovered || selected ? "opacity-100" : "opacity-0",
        )}
      />
      {selected && (
        <div
          role="toolbar"
          aria-label={label}
          className={cn(toolbarClass, "top-[-42px] left-0 items-center")}
        >
          <span className="text-ink-3 pr-2 pl-1.5 font-semibold">{label}</span>
          <button
            type="button"
            aria-label={t("documents.page.moveUp")}
            title={t("documents.page.moveUp")}
            onClick={() => move(-1)}
            className={toolButtonClass}
          >
            <UpIcon />
          </button>
          <button
            type="button"
            aria-label={t("documents.page.moveDown")}
            title={t("documents.page.moveDown")}
            onClick={() => move(1)}
            className={toolButtonClass}
          >
            <DownIcon />
          </button>
          <span className="relative flex">
            <button
              type="button"
              aria-expanded={moving}
              onClick={() => toggleMoving(block.id)}
              className={cn(toolButtonClass, "px-2 font-[inherit]")}
            >
              <MoveIcon />
              {t("documents.page.moveTo")}
            </button>
            {moving && (
              <div
                role="menu"
                aria-label={t("documents.page.moveTo")}
                className="bg-panel border-hair absolute top-9 left-0 z-10 flex min-w-[150px] flex-col rounded-[10px] border p-1.5 shadow-[0_10px_24px_rgba(28,25,23,0.18)]"
              >
                {page.arrangement
                  .filter(({ region }) => region !== current.region)
                  .map(({ region }) => (
                    <button
                      key={region}
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        toggleMoving(block.id);
                        arrange(
                          page,
                          relocate(
                            page.arrangement,
                            block.id,
                            region,
                            (blocks) => blocks.length,
                          ),
                        );
                      }}
                      className="text-ink cursor-pointer rounded-md border-0 bg-transparent px-2.5 py-2 text-left text-[13px]"
                    >
                      {t(`documents.page.regions.${region}`)}
                    </button>
                  ))}
              </div>
            )}
          </span>
          {section && (
            <button
              type="button"
              aria-label={t("documents.page.duplicate")}
              title={t("documents.page.duplicate")}
              onClick={() => {
                const copy = withNewIds(block);
                page.edit([
                  { kind: "insert_block", after: block.id, block: copy },
                  ...(savedFor(design, page.template.id)
                    ? [
                        {
                          kind: "update_design" as const,
                          design: withBlockAfter(
                            design,
                            page.template.id,
                            block.id,
                            copy.id,
                          ),
                        },
                      ]
                    : []),
                ]);
              }}
              className={toolButtonClass}
            >
              <DuplicateIcon />
            </button>
          )}
          {(section || block.kind === "photo") && (
            <button
              type="button"
              aria-label={t(
                section
                  ? "documents.page.deleteSection"
                  : "documents.page.removePhoto",
              )}
              title={t(
                section
                  ? "documents.page.deleteSection"
                  : "documents.page.removePhoto",
              )}
              onClick={() => {
                clearSelection();
                page.edit(
                  section
                    ? [
                        { kind: "delete", path: `blocks/${block.id}` },
                        ...((design.layouts ?? []).some((placement) =>
                          placement.blocks.includes(block.id),
                        )
                          ? [
                              {
                                kind: "update_design" as const,
                                design: withoutBlock(design, block.id),
                              },
                            ]
                          : []),
                      ]
                    : [
                        {
                          kind: "update_visibility",
                          block: block.id,
                          hidden: true,
                        },
                      ],
                );
              }}
              className={cn(toolButtonClass, "text-crit")}
            >
              <DeleteIcon />
            </button>
          )}
        </div>
      )}
      {children}
      {section && (hovered || selected) && <HotBar block={block} />}
    </Tag>
  );
}
