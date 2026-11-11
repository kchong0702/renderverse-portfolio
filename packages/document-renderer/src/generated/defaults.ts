/**
 * Generated code. Do not edit manually.
 *
 * Regenerate using: pnpm schema
 * Source: json_schemas()
 */

export const defaults = {
  Design: {
    template: "classic",
    accent: null,
    font: null,
    text_size: "medium",
    line_spacing: 1.3,
    alignment: "left",
    margins_mm: 16,
    section_spacing_pt: 12,
    page_size: "a4",
    photo_shape: "circle",
    photo_size: "medium",
  },
  GridArea: {
    column: 1,
    span: 12,
    row: 1,
    rows: 1,
  },
  RegionSpec: {
    fill: "none",
    divider: null,
    align: "left",
    title: "rule-after",
    entry: "inline",
    contacts: "line",
    skills: "inline",
    photo_ring: false,
  },
  TemplateSpec: {
    photo: "top",
  },
} as const;
