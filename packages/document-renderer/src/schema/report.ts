// Generated from document-schema by `pnpm schema`. Do not edit.

/**
 * Hash of the printed PDF
 */
export type RenderId = string;
/**
 * Number of pages
 */
export type Pages = number;
/**
 * How much of the last page is used
 */
export type LastPageFill = number;
/**
 * The block
 */
export type Block = string;
/**
 * Page it starts on
 */
export type FirstPage = number;
/**
 * Page it ends on
 */
export type LastPage = number;
/**
 * The pages each block runs across
 */
export type Spans = BlockSpan[];
/**
 * Warning kind
 */
export type Kind = "split_entry";
/**
 * The entry
 */
export type Path = string;
/**
 * The page it starts on and the page it ends on
 *
 * @minItems 2
 * @maxItems 2
 */
export type Pages1 = [unknown, unknown];
/**
 * Warning kind
 */
export type Kind1 = "orphan_heading";
/**
 * The section
 */
export type Block1 = string;
/**
 * Where the heading sits alone at the bottom
 */
export type Page = number;
/**
 * Warning kind
 */
export type Kind2 = "region_overflow";
/**
 * The region
 */
export type Region =
  "top" | "top-left" | "top-center" | "top-right" | "main" | "side";
/**
 * How far past the page it runs
 */
export type ByMm = number;
/**
 * Problems to fix before sending
 */
export type Warnings = (SplitEntry | OrphanHeading | RegionOverflow)[];

export interface Report {
  render_id: RenderId;
  pages: Pages;
  last_page_fill: LastPageFill;
  spans?: Spans;
  warnings?: Warnings;
}
export interface BlockSpan {
  block: Block;
  first_page: FirstPage;
  last_page: LastPage;
}
export interface SplitEntry {
  kind: Kind;
  path: Path;
  pages: Pages1;
}
export interface OrphanHeading {
  kind: Kind1;
  block: Block1;
  page: Page;
}
export interface RegionOverflow {
  kind: Kind2;
  region: Region;
  by_mm: ByMm;
}
