import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { compile } from "json-schema-to-typescript";

const banner =
  "// Generated from document-schema by `pnpm schema`. Do not edit.";
const schemas = JSON.parse(
  execFileSync("uv", [
    "run",
    "python",
    "-c",
    "import json; from document_schema import json_schemas; print(json.dumps(json_schemas()))",
  ]),
);
const write = (name, text) =>
  writeFileSync(new URL(`../src/schema/${name}.ts`, import.meta.url), text);

for (const [name, title] of [
  ["document", "AnyDocument"],
  ["template", "TemplateSpec"],
  ["report", "Report"],
]) {
  write(
    name,
    await compile({ ...schemas[name], title }, title, {
      additionalProperties: false,
      bannerComment: banner,
    }),
  );
}

const models = {
  ...schemas.document.$defs,
  ...schemas.template.$defs,
  TemplateSpec: schemas.template,
};
const defaults = Object.fromEntries(
  ["Design", "GridArea", "RegionSpec", "TemplateSpec"].map((model) => [
    model,
    Object.fromEntries(
      Object.entries(models[model].properties)
        .filter(([, property]) => "default" in property)
        .map(([field, property]) => [field, property.default]),
    ),
  ]),
);
write(
  "defaults",
  `${banner}\n\nexport const defaults = ${JSON.stringify(defaults, null, 2)} as const;\n`,
);
