import type { ElementProps, Region } from "@renderverse/document-renderer";
import { useTranslation } from "react-i18next";
import { relocate } from "../../lib/arrangement";
import { useEditorStore } from "../../state/editorStore";
import { arrange, usePage } from "./PageContext";

export default function RegionFrame({
  region,
  props: { style, ...props },
}: {
  region: Region;
  props: ElementProps;
}) {
  const { t } = useTranslation();
  const page = usePage();
  const key = `r:${region}`;
  const dragging = useEditorStore((state) => state.drag?.kind === "k");
  const over = useEditorStore((state) => state.dropKey === key);
  const { dropOver, endDrag } = useEditorStore.getState();
  const empty = !page.arrangement.find((placed) => placed.region === region)
    ?.blocks.length;

  return (
    <section
      {...props}
      aria-label={t(`documents.page.regions.${region}`)}
      onDragOver={(event) => {
        if (!dragging) return;
        event.preventDefault();
        dropOver(key);
      }}
      onDrop={(event) => {
        const drag = useEditorStore.getState().drag;
        if (drag?.kind !== "k") return;
        event.preventDefault();
        endDrag();
        arrange(
          page,
          relocate(
            page.arrangement,
            drag.id,
            region,
            (blocks) => blocks.length,
          ),
        );
      }}
      style={{
        ...style,
        outline: dragging
          ? over
            ? "calc(2px * var(--unzoom)) solid #B45309"
            : "calc(1.5px * var(--unzoom)) dashed rgba(180, 83, 9, 0.5)"
          : undefined,
        outlineOffset: "calc(-3px * var(--unzoom))",
        minHeight: dragging && empty ? "3em" : undefined,
      }}
    />
  );
}
