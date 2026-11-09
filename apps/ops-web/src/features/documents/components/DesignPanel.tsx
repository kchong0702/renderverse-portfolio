import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib/cn";
import { SelectField } from "@/shared/components/fields";
import Segmented from "@/shared/components/Segmented";
import type {
  Alignment,
  Design,
  DocumentRecord,
  Font,
  PageSize,
  Size,
} from "../api/documents";
import { useTemplates } from "../hooks/useDocuments";
import RangeField from "./RangeField";

const ACCENTS = ["#1F3A5F", "#0F5E5A", "#7A1F2B", "#3F3F46"];

const FONTS: Font[] = [
  "inter",
  "lato",
  "source-sans-3",
  "source-serif-4",
  "merriweather",
  "eb-garamond",
];

interface DesignPanelProps {
  document: DocumentRecord;
  onChange: (design: Design) => void;
}

export default function DesignPanel({ document, onChange }: DesignPanelProps) {
  const { t } = useTranslation();
  const templates = useTemplates(document.kind);
  const design = document.body.design;
  const template = templates.data?.find((spec) => spec.id === design.template);
  const change = (patch: Partial<Design>) => onChange({ ...design, ...patch });

  return (
    <div className="flex flex-col gap-6">
      <section
        aria-labelledby="design-template"
        className="flex flex-col gap-2.5"
      >
        <div className="flex flex-col gap-0.5">
          <h3 id="design-template" className="m-0 text-sm font-semibold">
            {t("documents.design.template")}
          </h3>
          <span className="text-ink-3 text-[13px]">
            {t("documents.design.templateHint")}
          </span>
        </div>
        {templates.isError ? (
          <p role="alert" className="text-crit m-0 text-sm">
            {t("documents.design.templatesFailed", {
              reason: templates.error.message,
            })}
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {templates.data?.map((spec) => (
              <button
                key={spec.id}
                type="button"
                aria-pressed={spec.id === design.template}
                onClick={() => change({ template: spec.id, accent: null })}
                className={cn(
                  "bg-panel flex cursor-pointer flex-col gap-1.5 rounded-[10px] border p-3 text-left",
                  spec.id === design.template
                    ? "border-amber ring-amber ring-1"
                    : "border-hair",
                )}
              >
                <span
                  aria-hidden="true"
                  className="h-1.5 w-1/2 rounded-sm"
                  style={{ background: spec.accent }}
                />
                <span className="text-sm font-semibold">{spec.name}</span>
                <span className="text-ink-3 text-xs">{spec.description}</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section
        aria-labelledby="design-accent"
        className="flex flex-col gap-2.5"
      >
        <h3 id="design-accent" className="m-0 text-sm font-semibold">
          {t("documents.design.accent")}
        </h3>
        <div className="flex flex-wrap gap-2.5">
          {[null, ...ACCENTS].map((hex) => (
            <button
              key={hex ?? "template"}
              type="button"
              aria-pressed={design.accent === hex}
              aria-label={
                hex
                  ? t("documents.design.accentColour", { hex })
                  : t("documents.design.templateAccent")
              }
              onClick={() => change({ accent: hex })}
              className={cn(
                "size-8 cursor-pointer rounded-full border-2",
                design.accent === hex ? "border-ink" : "border-transparent",
              )}
              style={{ background: hex ?? template?.accent ?? "transparent" }}
            />
          ))}
        </div>
      </section>

      <section aria-labelledby="design-text" className="flex flex-col gap-3.5">
        <h3 id="design-text" className="m-0 text-sm font-semibold">
          {t("documents.design.text")}
        </h3>
        <SelectField
          label={t("documents.design.font")}
          value={design.font ?? ""}
          options={[
            {
              value: "",
              label: template
                ? t("documents.design.templateFont", {
                    font: t(`documents.fonts.${template.body_font}`),
                  })
                : t("documents.design.templateFontPlain"),
            },
            ...FONTS.map((font) => ({
              value: font,
              label: t(`documents.fonts.${font}`),
            })),
          ]}
          onChange={(event) =>
            change({
              font: FONTS.find((font) => font === event.target.value) ?? null,
            })
          }
        />
        <div className="flex flex-col gap-1.5">
          <span className="text-ink-3 text-sm">
            {t("documents.design.textSize")}
          </span>
          <Segmented<Size>
            label={t("documents.design.textSize")}
            value={design.text_size}
            options={(["small", "medium", "large"] as const).map((size) => ({
              value: size,
              label: t(`documents.design.sizes.${size}`),
            }))}
            onChange={(text_size) => change({ text_size })}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-ink-3 text-sm">
            {t("documents.design.alignment")}
          </span>
          <Segmented<Alignment>
            label={t("documents.design.alignment")}
            value={design.alignment}
            options={(["left", "justify"] as const).map((alignment) => ({
              value: alignment,
              label: t(`documents.design.alignments.${alignment}`),
            }))}
            onChange={(alignment) => change({ alignment })}
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
      </section>

      <section
        aria-labelledby="design-layout"
        className="flex flex-col gap-3.5"
      >
        <h3 id="design-layout" className="m-0 text-sm font-semibold">
          {t("documents.design.layout")}
        </h3>
        <div className="flex flex-col gap-1.5">
          <span className="text-ink-3 text-sm">
            {t("documents.design.pageSize")}
          </span>
          <Segmented<PageSize>
            label={t("documents.design.pageSize")}
            value={design.page_size}
            options={(["a4", "letter"] as const).map((size) => ({
              value: size,
              label: t(`documents.design.pageSizes.${size}`),
            }))}
            onChange={(page_size) => change({ page_size })}
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
      </section>
    </div>
  );
}
