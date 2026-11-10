import { Eye, EyeOff } from "lucide-react";
import { lazy, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { useMe } from "@/features/auth";
import DraftTextField from "@/shared/components/DraftTextField";
import type { Block, DocumentRecord, Edit } from "../api/documents";
import { blockKind, FIELD_KEYS, textEntries } from "../lib/fields";

const RichTextField = lazy(() => import("./RichTextField"));

interface ContentPanelProps {
  document: DocumentRecord;
  onEdit: (edits: Edit[]) => void;
}

export default function ContentPanel({ document, onEdit }: ContentPanelProps) {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const source = `user:${me?.id ?? "owner"}`;

  const label = (key: string) => {
    const known = FIELD_KEYS.find((k) => k === key);
    return known ? t(`documents.fields.${known}`) : key;
  };
  const blockLabel = (block: Block) => {
    const kind = blockKind(block.kind);
    return kind ? t(`documents.blocks.${kind}`) : block.kind;
  };

  return (
    <Suspense>
      <div className="flex flex-col gap-5">
        <p className="text-ink-3 m-0 text-sm">{t("documents.content.hint")}</p>
        {document.body.content.blocks.map((block) => (
          <section
            key={block.id}
            aria-label={blockLabel(block)}
            className={`border-hair-soft flex flex-col gap-3 border-b pb-5 ${block.hidden ? "opacity-60" : ""}`}
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className="m-0 text-sm font-semibold">{blockLabel(block)}</h3>
              <button
                type="button"
                aria-pressed={!block.hidden}
                aria-label={t(
                  block.hidden
                    ? "documents.content.show"
                    : "documents.content.hide",
                  { block: blockLabel(block) },
                )}
                onClick={() =>
                  onEdit([
                    {
                      kind: "update_visibility",
                      block: block.id,
                      hidden: !block.hidden,
                    },
                  ])
                }
                className="text-ink-3 hover:text-ink inline-flex size-9 cursor-pointer items-center justify-center rounded-lg"
              >
                {block.hidden ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            {textEntries(block).map((entry) => (
              <div
                key={entry.path}
                style={{ paddingLeft: `${Math.min(entry.depth, 3) * 14}px` }}
              >
                {"html" in entry.value ? (
                  <RichTextField
                    label={label(entry.label)}
                    value={entry.value.html}
                    onSave={(html) =>
                      onEdit([
                        {
                          kind: "update_field",
                          path: entry.path,
                          value: {
                            html,
                            align:
                              "html" in entry.value
                                ? (entry.value.align ?? null)
                                : null,
                            src: [source],
                          },
                        },
                      ])
                    }
                  />
                ) : (
                  <DraftTextField
                    label={label(entry.label)}
                    value={entry.value.text}
                    onSave={(text) =>
                      onEdit([
                        {
                          kind: "update_field",
                          path: entry.path,
                          value: { text, src: [source] },
                        },
                      ])
                    }
                  />
                )}
              </div>
            ))}
          </section>
        ))}
      </div>
    </Suspense>
  );
}
