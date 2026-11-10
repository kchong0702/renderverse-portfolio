import type { Design, Font } from "@renderverse/document-renderer";
import { templates } from "@renderverse/document-renderer";
import { useId, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { buttonClass } from "@/shared/components/button";
import { cn } from "@/shared/lib/cn";
import type { DocumentRecord, Edit } from "../api/documents";
import {
  families,
  familyOf,
  membersOf,
  sideColumn,
  structureOf,
} from "../lib/templates";
import { useEditorStore } from "../state/editorStore";
import { PersonIcon } from "./page/icons";
import RangeField from "./RangeField";
import TemplateThumbnail from "./TemplateThumbnail";

const ACCENTS = [
  ["navy", "#1F3A5F"],
  ["teal", "#0F5E5A"],
  ["maroon", "#7A1F2B"],
  ["graphite", "#3F3F46"],
] as const;

const FONTS: Font[] = [
  "source-sans-3",
  "eb-garamond",
  "lato",
  "merriweather",
  "inter",
  "source-serif-4",
];

const groupClass = "border-hair-soft flex flex-col gap-3 border-t pt-[18px]";

function Segmented<T extends string>({
  label,
  value,
  options,
  onPick,
  className,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onPick: (value: T) => void;
  className?: string;
}) {
  const id = useId();
  return (
    <div
      role="group"
      aria-labelledby={id}
      className={cn("flex flex-[1_1_140px] flex-col gap-1.5", className)}
    >
      <span id={id} className="text-ink-3 text-[13px]">
        {label}
      </span>
      <div className="bg-chip flex rounded-[10px] p-[3px]">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={option.value === value}
            onClick={() => onPick(option.value)}
            className={cn(
              "min-h-[34px] flex-1 cursor-pointer rounded-lg border-0 text-[13px]",
              option.value === value
                ? "bg-panel text-ink shadow-card font-semibold"
                : "text-ink-3 bg-transparent font-medium",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Group({
  heading,
  note,
  className,
  children,
}: {
  heading: string;
  note?: string;
  className: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div role="group" aria-labelledby={id} className={className}>
      <div className="flex flex-col gap-0.5">
        <h2 id={id} className="m-0 text-[15px] font-semibold">
          {heading}
        </h2>
        {note && <span className="text-ink-3 text-[13px]">{note}</span>}
      </div>
      {children}
    </div>
  );
}

export default function DesignPanel({
  document,
  onDesign,
  onEdit,
}: {
  document: DocumentRecord;
  onDesign: (design: Design) => void;
  onEdit: (edits: Edit[]) => void;
}) {
  const { t } = useTranslation();
  const clearSelection = useEditorStore((state) => state.clearSelection);
  const design = document.body.design;
  const template = templates[design.template] ?? templates.classic;
  const family = familyOf(template.id);
  const members = membersOf(family);
  const columns =
    members.filter((member) => !sideColumn(member)).length > 0 &&
    members.some((member) => sideColumn(member));
  const sides = members.filter((member) => sideColumn(member));
  const photo = document.body.content.blocks.find(
    (block) => block.kind === "photo",
  );
  const shown = photo && !photo.hidden;
  const change = (patch: Partial<Design>) => onDesign({ ...design, ...patch });
  const spot = template.photo ?? "top";
  const where =
    template.layout.photo === "side"
      ? "side"
      : spot === "top"
        ? "top"
        : "header";

  return (
    <div className="flex flex-col gap-6 p-5">
      <Group
        heading={t("documents.design.template")}
        note={t("documents.design.templateHint")}
        className="flex flex-col gap-2.5"
      >
        <div className="grid grid-cols-2 gap-3">
          {families.map((spec) => (
            <button
              key={spec.id}
              type="button"
              aria-pressed={spec.id === family.id}
              onClick={() => {
                clearSelection();
                change({ template: spec.id, accent: null });
              }}
              className={cn(
                "bg-panel text-ink flex cursor-pointer flex-col gap-2 rounded-[10px] border p-1.5 text-left",
                spec.id === family.id
                  ? "border-amber shadow-[0_0_0_1px_var(--color-amber)]"
                  : "border-hair",
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  "border-hair-soft flex aspect-[4/3] flex-col gap-[5px] overflow-hidden rounded-md border bg-white",
                  { stack: "p-2.5", band: "p-0", header: "p-2" }[
                    structureOf(spec)
                  ],
                )}
              >
                <TemplateThumbnail template={spec} />
              </span>
              <span className="flex flex-col gap-px px-1 pb-1">
                <span className="text-[13px] font-semibold">{spec.name}</span>
                <span className="text-ink-3 text-xs leading-[1.4]">
                  {spec.description}
                </span>
              </span>
            </button>
          ))}
        </div>
      </Group>

      <Group
        heading={t("documents.design.accent")}
        className="flex flex-col gap-2.5"
      >
        <div className="flex flex-wrap gap-2.5">
          {[[null, template.accent] as const, ...ACCENTS].map(([name, hex]) => (
            <button
              key={name ?? "template"}
              type="button"
              aria-pressed={design.accent === (name && hex)}
              aria-label={t(`documents.design.accents.${name ?? "template"}`)}
              title={t(`documents.design.accents.${name ?? "template"}`)}
              onClick={() => change({ accent: name && hex })}
              className="border-panel size-[34px] cursor-pointer rounded-full border-[3px] p-0"
              style={{
                background: hex,
                boxShadow: `0 0 0 2px ${design.accent === (name && hex) ? "var(--color-ink)" : "transparent"}`,
              }}
            />
          ))}
        </div>
        <span className="text-ink-3 text-xs">
          {t("documents.design.accentNote")}
        </span>
      </Group>

      <Group heading={t("documents.design.text")} className={groupClass}>
        <label className="flex flex-col gap-1.5">
          <span className="text-ink-3 text-[13px]">
            {t("documents.design.font")}
          </span>
          <select
            value={design.font ?? ""}
            onChange={(event) =>
              change({
                font: FONTS.find((font) => font === event.target.value) ?? null,
              })
            }
            className="border-hair bg-ground text-ink min-h-10 rounded-lg border px-3 text-sm"
          >
            <option value="">
              {t("documents.design.templateFont", {
                font: t(`documents.fonts.${template.body_font}`),
              })}
            </option>
            {FONTS.map((font) => (
              <option key={font} value={font}>
                {t(`documents.fonts.${font}`)}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-3">
          <Segmented
            label={t("documents.design.textSize")}
            value={design.text_size}
            options={(["small", "medium", "large"] as const).map((size) => ({
              value: size,
              label: t(`documents.design.sizes.${size}`),
            }))}
            onPick={(text_size) => change({ text_size })}
          />
          <Segmented
            label={t("documents.design.alignment")}
            value={design.alignment}
            options={(["left", "justify"] as const).map((alignment) => ({
              value: alignment,
              label: t(`documents.design.alignments.${alignment}`),
            }))}
            onPick={(alignment) => change({ alignment })}
          />
        </div>
        <RangeField
          label={t("documents.design.lineSpacing")}
          value={design.line_spacing}
          min={1.05}
          max={1.7}
          step={0.05}
          format={(value) => value.toFixed(2)}
          onSave={(line_spacing) => change({ line_spacing })}
        />
      </Group>

      <Group heading={t("documents.design.layout")} className={groupClass}>
        <div className="flex flex-wrap gap-3">
          {columns && (
            <Segmented
              label={t("documents.design.columns")}
              value={sideColumn(template) ? "two" : "one"}
              options={(["one", "two"] as const).map((count) => ({
                value: count,
                label: t(`documents.design.columnCounts.${count}`),
              }))}
              onPick={(count) =>
                change({
                  template: members.find(
                    (member) => !!sideColumn(member) === (count === "two"),
                  )!.id,
                })
              }
            />
          )}
          {sides.length > 1 && sideColumn(template) && (
            <Segmented
              label={t("documents.design.sidebar")}
              value={sideColumn(template) === 1 ? "left" : "right"}
              options={(["left", "right"] as const).map((side) => ({
                value: side,
                label: t(`documents.design.sides.${side}`),
              }))}
              onPick={(side) =>
                change({
                  template: sides.find(
                    (member) =>
                      (sideColumn(member) === 1) === (side === "left"),
                  )!.id,
                })
              }
            />
          )}
          <Segmented
            label={t("documents.design.pageSize")}
            value={design.page_size}
            options={(["a4", "letter"] as const).map((size) => ({
              value: size,
              label: t(`documents.design.pageSizes.${size}`),
            }))}
            onPick={(page_size) => change({ page_size })}
          />
        </div>
        <RangeField
          label={t("documents.design.margins")}
          value={design.margins_mm}
          min={8}
          max={25}
          step={1}
          format={(value) => t("documents.design.mm", { value })}
          onSave={(margins_mm) => change({ margins_mm })}
        />
        <RangeField
          label={t("documents.design.sectionSpacing")}
          value={design.section_spacing_pt}
          min={4}
          max={24}
          step={1}
          format={(value) => t("documents.design.pt", { value })}
          onSave={(section_spacing_pt) => change({ section_spacing_pt })}
        />
      </Group>

      <Group
        heading={t("documents.design.photo")}
        note={
          shown
            ? t("documents.design.photoMoved")
            : spot === "none"
              ? t("documents.design.photoNone", { template: family.name })
              : t("documents.design.photoHint", {
                  template: family.name,
                  where: t(`documents.design.photoWhere.${where}`),
                })
        }
        className={groupClass}
      >
        {shown ? (
          <>
            <div className="flex flex-wrap gap-3">
              <Segmented
                label={t("documents.design.shape")}
                value={design.photo_shape}
                options={(["circle", "rounded", "square"] as const).map(
                  (shape) => ({
                    value: shape,
                    label: t(`documents.design.shapes.${shape}`),
                  }),
                )}
                onPick={(photo_shape) => change({ photo_shape })}
                className="flex-[1_1_160px]"
              />
              <Segmented
                label={t("documents.design.size")}
                value={design.photo_size}
                options={(["small", "medium", "large"] as const).map(
                  (size) => ({
                    value: size,
                    label: t(`documents.design.photoSizes.${size}`),
                  }),
                )}
                onPick={(photo_size) => change({ photo_size })}
              />
            </div>
            <button
              type="button"
              onClick={() =>
                onEdit([
                  { kind: "update_visibility", block: photo.id, hidden: true },
                ])
              }
              className="border-hair bg-panel text-crit inline-flex min-h-9 cursor-pointer items-center self-start rounded-lg border px-3.5 text-[13px] font-semibold"
            >
              {t("documents.design.removePhoto")}
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={
              photo
                ? () =>
                    onEdit([
                      {
                        kind: "update_visibility",
                        block: photo.id,
                        hidden: false,
                      },
                    ])
                : undefined
            }
            className={cn(buttonClass(), "self-start")}
          >
            <PersonIcon />
            {t("documents.design.addPhoto")}
          </button>
        )}
      </Group>
    </div>
  );
}
