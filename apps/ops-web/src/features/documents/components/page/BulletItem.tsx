import type { Bullet } from "@renderverse/document-renderer";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { afterFor, entryAt, newId } from "../../lib/items";
import { useEditorStore } from "../../state/editorStore";
import RichTextField from "../RichTextField";
import { dropLine } from "./chrome";
import Handle from "./Handle";
import { usePage } from "./PageContext";

export default function BulletItem({
  path: entryPath,
  bullet,
}: {
  path: string;
  bullet: Bullet;
}) {
  const { t } = useTranslation();
  const page = usePage();
  const path = `${entryPath}/bullets/${bullet.id}`;
  const key = `b:${path}`;
  const hovered = useEditorStore((state) => state.hovered.bullet === path);
  const drag = useEditorStore((state) => state.drag);
  const over = useEditorStore((state) => state.dropKey === key);
  const { enter, leave, startDrag, dropOver, endDrag, focusNext } =
    useEditorStore.getState();
  const bullets =
    entryAt(page.record.body.content.blocks, entryPath)?.item?.bullets ?? [];
  const ids = bullets.map((each) => each.id);

  return (
    <li
      onMouseEnter={() => enter("bullet", path)}
      onMouseLeave={() => leave("bullet", path)}
      onDragOver={(event) => {
        if (drag?.kind !== "b") return;
        event.preventDefault();
        event.stopPropagation();
        dropOver(key);
      }}
      onDrop={(event) => {
        if (drag?.kind !== "b") return;
        event.preventDefault();
        event.stopPropagation();
        endDrag();
        if (drag.id === path) return;
        const from = drag.id.split("/bullets/");
        const moved = entryAt(
          page.record.body.content.blocks,
          from[0],
        )?.item?.bullets?.find((each) => each.id === from[1]);
        if (!moved) return;
        const after = afterFor(ids, moved.id, bullet.id);
        page.edit(
          from[0] === entryPath
            ? [{ kind: "move", path: drag.id, after }]
            : [
                { kind: "delete", path: drag.id },
                {
                  kind: "insert_item",
                  parent: `${entryPath}/bullets`,
                  after,
                  item: moved,
                },
              ],
        );
      }}
      style={{
        position: "relative",
        boxShadow: over && drag?.id !== path ? dropLine : undefined,
      }}
    >
      <Handle
        icon={9}
        dot={2.2}
        aria-label={t("documents.page.dragBullet")}
        title={t("documents.page.dragBulletTitle")}
        onDragStart={(event) => {
          event.stopPropagation();
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", path);
          startDrag({ kind: "b", id: path });
        }}
        onDragEnd={endDrag}
        className={cn(
          "top-[0.1em] right-[calc(100%+1.2em)] h-4 w-3 rounded-[3px] bg-transparent text-[#A8A29E]",
          hovered ? "opacity-100" : "opacity-0",
        )}
      />
      <RichTextField
        path={`${path}/text`}
        value={bullet.text}
        onSplit={(html) => {
          const next = { id: newId(), text: { html: "", src: [page.source] } };
          focusNext(`${entryPath}/bullets/${next.id}/text`);
          page.edit([
            ...(html === bullet.text.html
              ? []
              : [
                  {
                    kind: "update_field" as const,
                    path: `${path}/text`,
                    value: { ...bullet.text, html, src: [page.source] },
                  },
                ]),
            {
              kind: "insert_item",
              parent: `${entryPath}/bullets`,
              after: bullet.id,
              item: next,
            },
          ]);
        }}
        onRemove={(refocus) => {
          const previous = ids[ids.indexOf(bullet.id) - 1];
          if (refocus && previous)
            focusNext(`${entryPath}/bullets/${previous}/text`);
          page.edit([{ kind: "delete", path }]);
        }}
      />
    </li>
  );
}
