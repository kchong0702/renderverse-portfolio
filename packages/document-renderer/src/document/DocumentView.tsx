import type { CSSProperties, ReactNode } from "react";
import { blocks } from "../blocks";
import { defaults } from "../generated/defaults";
import type { AnyDocument, Design, Font } from "../generated/document";
import type { TemplateSpec } from "../generated/template";
import { translator } from "../../i18n";
import { place, type AnyBlock, type PlacedRegion } from "../layout/place";
import type { Context } from "../types";

export const GUTTER_MM = 6;

export const PAGE_MM = { a4: [210, 297], letter: [215.9, 279.4] } as const;

const fontFamilies: Record<Font, string> = {
  inter: '"Inter", sans-serif',
  lato: '"Lato", sans-serif',
  "source-sans-3": '"Source Sans 3", sans-serif',
  "source-serif-4": '"Source Serif 4", serif',
  merriweather: '"Merriweather", serif',
  "eb-garamond": '"EB Garamond", serif',
};

export const designOf = (document: AnyDocument) =>
  ({ ...defaults.Design, ...document.design }) as Required<Design>;

const rowCountOf = (regions: PlacedRegion[]) =>
  Math.max(...regions.map(({ spec: { area } }) => area.row + area.rows - 1));

const fillsPageHeight = (
  { spec: { fill, area } }: PlacedRegion,
  rowCount: number,
) => fill !== "none" && area.row === 1 && area.rows === rowCount;

export function pageCss(document: AnyDocument, template: TemplateSpec): string {
  const design = designOf(document);
  const regions = place(document, template);
  const [width] = PAGE_MM[design.page_size];
  const margin = design.margins_mm;
  const column = (width - 2 * margin - 11 * GUTTER_MM) / 12;
  const accent = design.accent ?? template.accent;
  const bands = regions
    .filter((region) => fillsPageHeight(region, rowCountOf(regions)))
    .map(({ spec: { area, fill } }) => {
      const end = area.column + area.span - 1;
      const from =
        area.column === 1
          ? 0
          : margin + (area.column - 1) * (column + GUTTER_MM) - GUTTER_MM / 2;
      const to =
        end === 12
          ? width
          : margin + end * column + (end - 1) * GUTTER_MM + GUTTER_MM / 2;
      const colour =
        fill === "accent" ? accent : `color-mix(in srgb, ${accent} 12%, white)`;
      const [x0, x1] = [from, to].map((x) => `${+x.toFixed(2)}mm`);
      return `linear-gradient(to right, transparent ${x0}, ${colour} ${x0}, ${colour} ${x1}, transparent ${x1})`;
    });
  return [
    `@page { size: ${design.page_size === "a4" ? "A4" : "letter"}; margin: ${margin}mm 0; }`,
    bands.length ? `.pagedjs_page { background: ${bands.join(", ")}; }` : "",
  ].join("\n");
}

export interface DocumentViewProps {
  document: AnyDocument;
  template: TemplateSpec;
  assetUrl: (hash: string) => string;
}

export function DocumentView({
  document,
  template,
  assetUrl,
}: DocumentViewProps) {
  const design = designOf(document);
  const regions = place(document, template);
  const rowCount = rowCountOf(regions);
  const t = translator(document.language);
  const style = {
    "--accent": design.accent ?? template.accent,
    "--body-font": fontFamilies[design.font ?? template.body_font],
    "--heading-font": fontFamilies[design.font ?? template.heading_font],
    "--text-size": { small: "9.5pt", medium: "10.5pt", large: "11.5pt" }[
      design.text_size
    ],
    "--line": design.line_spacing,
    "--margin": `${design.margins_mm}mm`,
    "--gutter": `${GUTTER_MM}mm`,
    "--space": `${design.section_spacing_pt}pt`,
    "--photo-size": { small: "24mm", medium: "32mm", large: "40mm" }[
      design.photo_size
    ],
    "--photo-radius": { circle: "50%", rounded: "14%", square: "0" }[
      design.photo_shape
    ],
  } as CSSProperties;

  return (
    <div className="dr-page" style={style} data-align={design.alignment}>
      {regions.map((region) => {
        const { area, ...spec } = region.spec;
        const ctx: Context = {
          document,
          spec: region.spec,
          photo: template.photo ?? defaults.TemplateSpec.photo,
          assetUrl,
          t,
        };
        const bleed = {
          "--bleed-left":
            area.column === 1 ? "var(--margin)" : "calc(var(--gutter) / 2)",
          "--bleed-right":
            area.column + area.span === 13
              ? "var(--margin)"
              : "calc(var(--gutter) / 2)",
          "--bleed-top": area.row === 1 ? "var(--margin)" : "0mm",
        };
        return (
          <section
            key={region.region}
            className="dr-region"
            data-region={region.region}
            data-flows={region.flows}
            data-band={fillsPageHeight(region, rowCount)}
            data-fill={spec.fill}
            data-divider={spec.divider ?? undefined}
            data-align={spec.align}
            data-title={spec.title}
            data-skills={spec.skills}
            data-floats={
              ctx.photo !== "top" &&
              region.blocks.some((block) => block.kind === "photo")
            }
            style={
              {
                gridColumn: `${area.column} / span ${area.span}`,
                gridRow: `${area.row} / span ${area.rows}`,
                ...bleed,
              } as CSSProperties
            }
          >
            {region.blocks.map((block) => {
              const Block = blocks[block.kind] as (props: {
                block: AnyBlock;
                ctx: Context;
              }) => ReactNode;
              return <Block key={block.id} block={block} ctx={ctx} />;
            })}
          </section>
        );
      })}
    </div>
  );
}
