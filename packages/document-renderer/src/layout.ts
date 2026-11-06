import type {
  AnyDocument,
  LetterContent,
  ResumeContent,
} from "./schema/document";
import { defaults } from "./schema/defaults";
import type {
  GridArea,
  Region,
  RegionSpec,
  TemplateSpec,
} from "./schema/template";

export type AnyBlock =
  ResumeContent["blocks"][number] | LetterContent["blocks"][number];

export type Spec = Required<Omit<RegionSpec, "area">> & {
  area: Required<GridArea>;
};

export interface PlacedRegion {
  region: Region;
  spec: Spec;
  blocks: AnyBlock[];
  /** The region that runs onto later pages; the others must fit on the first */
  flows: boolean;
}

/** Puts each shown block in a region: the user's layout first, then the template's home; a photo leads its region */
export function place(
  document: AnyDocument,
  template: TemplateSpec,
): PlacedRegion[] {
  const regions = template.regions as Partial<Record<Region, RegionSpec>>;
  const home = template.home as Partial<
    Record<AnyBlock["kind"] | "default", Region>
  >;
  const photo = template.photo ?? defaults.TemplateSpec.photo;
  const left = new Map<string, AnyBlock>(
    document.content.blocks
      .filter(
        (block) =>
          !block.hidden && !(block.kind === "photo" && photo === "none"),
      )
      .map((block) => [block.id, block]),
  );
  const placed = new Map<Region, AnyBlock[]>(
    Object.keys(regions).map((region) => [region as Region, []]),
  );
  for (const [region, ids] of Object.entries(
    document.design?.layouts?.[template.id] ?? {},
  )) {
    for (const id of placed.has(region as Region) ? ids : []) {
      const block = left.get(id);
      if (block) {
        placed.get(region as Region)!.push(block);
        left.delete(id);
      }
    }
  }
  for (const block of left.values())
    placed.get(home[block.kind] ?? home.default!)!.push(block);

  return [...placed]
    .map(([region, blocks]) => ({
      region,
      blocks: [...blocks].sort(
        (a, b) => Number(b.kind === "photo") - Number(a.kind === "photo"),
      ),
      flows: region === home.default,
      spec: {
        ...defaults.RegionSpec,
        ...regions[region],
        area: { ...defaults.GridArea, ...regions[region]!.area },
      } as Spec,
    }))
    .sort(
      (a, b) =>
        Number(a.flows) - Number(b.flows) ||
        a.spec.area.row - b.spec.area.row ||
        a.spec.area.column - b.spec.area.column,
    );
}
