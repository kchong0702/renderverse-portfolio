/**
 * Generated code. Do not edit manually.
 *
 * Regenerate using: pnpm schema
 * Source: json_schemas()
 */

export type Region =
  "top" | "top-left" | "top-center" | "top-right" | "main" | "side";

export interface Report {
  render_id: string;
  pages: number;
  last_page_fill: number;
  spans?: BlockSpan[];
  warnings?: (SplitEntry | OrphanHeading | RegionOverflow)[];
}
export interface BlockSpan {
  block: string;
  first_page: number;
  last_page: number;
}
export interface SplitEntry {
  kind: "split_entry";
  path: string;
  pages: [number, number];
}
export interface OrphanHeading {
  kind: "orphan_heading";
  block: string;
  page: number;
}
export interface RegionOverflow {
  kind: "region_overflow";
  region: Region;
  by_mm: number;
}
