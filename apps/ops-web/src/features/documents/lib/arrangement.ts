import {
  place,
  type AnyDocument,
  type Design,
  type Region,
  type TemplateSpec,
} from "@renderverse/document-renderer";

export type Arrangement = { region: Region; blocks: string[] }[];

const insertAt = (blocks: string[], index: number, block: string) => [
  ...blocks.slice(0, index),
  block,
  ...blocks.slice(index),
];

export const arrangementOf = (
  document: AnyDocument,
  template: TemplateSpec,
): Arrangement =>
  place(document, template).map(({ region, blocks }) => ({
    region,
    blocks: blocks.map((block) => block.id),
  }));

export const regionOf = (arrangement: Arrangement, block: string) =>
  arrangement.find(({ blocks }) => blocks.includes(block))!;

export function relocate(
  arrangement: Arrangement,
  block: string,
  region: Region,
  index: (blocks: string[]) => number,
): Arrangement {
  const without = arrangement.map((placed) => ({
    ...placed,
    blocks: placed.blocks.filter((id) => id !== block),
  }));
  return without.map((placed) =>
    placed.region === region
      ? {
          region,
          blocks: insertAt(
            placed.blocks,
            Math.min(Math.max(index(placed.blocks), 0), placed.blocks.length),
            block,
          ),
        }
      : placed,
  );
}

export const replaceTemplateLayout = (
  design: Design,
  template: string,
  arrangement: Arrangement,
): Design => ({
  ...design,
  layouts: [
    ...(design.layouts ?? []).filter(
      (placement) => placement.template !== template,
    ),
    ...arrangement.map(({ region, blocks }) => ({ template, region, blocks })),
  ],
});

export const savedFor = (design: Design, template: string) =>
  (design.layouts ?? []).some((placement) => placement.template === template);

export const withBlockAfter = (
  design: Design,
  template: string,
  after: string,
  block: string,
): Design => ({
  ...design,
  layouts: (design.layouts ?? []).map((placement) =>
    placement.template === template && placement.blocks.includes(after)
      ? {
          ...placement,
          blocks: insertAt(
            placement.blocks,
            placement.blocks.indexOf(after) + 1,
            block,
          ),
        }
      : placement,
  ),
});

export const withoutBlock = (design: Design, block: string): Design => ({
  ...design,
  layouts: (design.layouts ?? []).map((placement) => ({
    ...placement,
    blocks: placement.blocks.filter((id) => id !== block),
  })),
});
