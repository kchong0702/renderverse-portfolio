import { parse } from "yaml";
import type { TemplateSpec } from "../generated/template";

const files = import.meta.glob<string>("../../templates/*.yaml", {
  query: "?raw",
  import: "default",
  eager: true,
});

export const templates: Record<string, TemplateSpec> = Object.fromEntries(
  Object.values(files).map((text) => {
    const template = parse(text) as TemplateSpec;
    return [template.id, template];
  }),
);
