import { templates, type TemplateSpec } from "@renderverse/document-renderer";

const ORDER = ["classic", "serif", "compact", "sidebar-band", "photo-header"];

const rank = ({ id }: TemplateSpec) =>
  ORDER.includes(id) ? ORDER.indexOf(id) : ORDER.length;

export const families: TemplateSpec[] = Object.values(templates)
  .filter(
    (template) =>
      !Object.keys(templates).some((id) => template.id.startsWith(`${id}-`)),
  )
  .sort((a, b) => rank(a) - rank(b));

export const familyOf = (id: string) =>
  families.find(
    (family) => id === family.id || id.startsWith(`${family.id}-`),
  ) ?? families[0];

export const membersOf = (family: TemplateSpec) =>
  Object.values(templates).filter(
    (template) =>
      template.id === family.id || template.id.startsWith(`${family.id}-`),
  );

export const sideColumn = (template: TemplateSpec) =>
  template.regions.side?.area?.column;

export const structureOf = (template: TemplateSpec) =>
  template.regions.side?.fill === "accent"
    ? "band"
    : template.regions.top?.fill === "accent"
      ? "header"
      : "stack";
