import {
  entryFields,
  type AnyBlock,
  type EntryKind,
} from "@renderverse/document-renderer";
import { useTranslation } from "react-i18next";
import { savedFor, withBlockAfter } from "../../lib/arrangement";
import {
  INSERTS,
  isEntryBlock,
  newEntry,
  newSection,
  type NewText,
} from "../../lib/items";
import { useEditorStore } from "../../state/editorStore";
import { dashedPillClass, unzoom } from "./chrome";
import { usePage } from "./PageContext";

const NOUNS: Partial<Record<EntryKind, string>> = {
  experience: "experience",
  education: "education",
  projects: "project",
  certifications: "certification",
};

export default function HotBar({ block }: { block: AnyBlock }) {
  const { t } = useTranslation();
  const page = usePage();
  const inserting = useEditorStore((state) => state.inserting === block.id);
  const { toggleInserting, leave, focusNext } = useEditorStore.getState();
  const design = page.record.body.design;
  const text = t("documents.page.new", { returnObjects: true }) as NewText;

  return (
    <div
      className={`${unzoom} absolute top-full right-0 left-0 z-[5] flex h-[34px] items-center justify-center gap-2 font-sans`}
    >
      {isEntryBlock(block) && (
        <button
          type="button"
          onClick={() => {
            const item = newEntry(
              block.kind,
              text.placeholders[block.kind],
              block.kind === "education" ? null : text.entryBullet,
              page.source,
            );
            const parent = `blocks/${block.id}/items`;
            focusNext(`${parent}/${item.id}/${entryFields[block.kind].title}`);
            page.edit([
              {
                kind: "insert_item",
                parent,
                after: block.items?.at(-1)?.id ?? null,
                item,
              },
            ]);
          }}
          className={`${dashedPillClass} h-[22px]`}
        >
          {t("documents.page.add", {
            noun: NOUNS[block.kind] ?? t("documents.page.entryNoun"),
          })}
        </button>
      )}
      <button
        type="button"
        aria-expanded={inserting}
        onClick={() => toggleInserting(block.id)}
        className="h-[22px] cursor-pointer rounded-full border-0 bg-[#B45309] px-2.5 text-[11px] font-semibold text-white"
      >
        {t("documents.page.sectionBelow")}
      </button>
      {inserting && (
        <div
          role="menu"
          aria-label={t("documents.page.addSection")}
          className="bg-panel border-hair absolute top-8 left-1/2 z-10 flex min-w-[180px] -translate-x-1/2 flex-col rounded-[10px] border p-1.5 shadow-[0_10px_24px_rgba(28,25,23,0.18)]"
        >
          {INSERTS.map((insert) => (
            <button
              key={insert}
              type="button"
              role="menuitem"
              onClick={() => {
                const section = newSection(insert, text, page.source);
                toggleInserting(block.id);
                leave("block", block.id);
                page.edit([
                  { kind: "insert_block", after: block.id, block: section },
                  ...(savedFor(design, page.template.id)
                    ? [
                        {
                          kind: "update_design" as const,
                          design: withBlockAfter(
                            design,
                            page.template.id,
                            block.id,
                            section.id,
                          ),
                        },
                      ]
                    : []),
                ]);
              }}
              className="text-ink flex cursor-pointer flex-col items-start gap-px rounded-md border-0 bg-transparent px-2.5 py-2 text-left font-sans text-[13px] font-semibold"
            >
              {t(`documents.page.inserts.${insert}.label`)}
              <span className="text-ink-3 text-xs font-normal">
                {t(`documents.page.inserts.${insert}.note`)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
