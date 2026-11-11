import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { compile } from "json-schema-to-typescript";

const banner = `/**
 * Generated code. Do not edit manually.
 *
 * Regenerate using: pnpm schema
 * Source: json_schemas()
 */`;
const schemas = JSON.parse(
  execFileSync("uv", [
    "run",
    "python",
    "-c",
    "import json; from document_schema import json_schemas; print(json.dumps(json_schemas()))",
  ]),
);
const write = (name, text) =>
  writeFileSync(new URL(`../src/generated/${name}.ts`, import.meta.url), text);

const mapValues = (object, map) =>
  Object.fromEntries(
    Object.entries(object).map(([key, value]) => [key, map(value, key)]),
  );
const dropped = new Set(["title", "description", "default"]);
const plain = (schema) =>
  Array.isArray(schema)
    ? schema.map(plain)
    : typeof schema !== "object" || schema === null
      ? schema
      : Object.fromEntries(
          Object.entries(schema)
            .filter(([key]) => !dropped.has(key))
            .map(([key, value]) =>
              key === "properties"
                ? [key, mapValues(value, plain)]
                : key === "patternProperties"
                  ? ["additionalProperties", plain(Object.values(value)[0])]
                  : key === "$defs"
                    ? [
                        key,
                        mapValues(value, (model, name) => ({
                          ...plain(model),
                          title: name,
                        })),
                      ]
                    : key === "prefixItems"
                      ? ["items", plain(value)]
                      : [key, plain(value)],
            ),
        );

for (const [name, title] of [
  ["document", "AnyDocument"],
  ["template", "TemplateSpec"],
  ["report", "Report"],
]) {
  const types = await compile({ ...plain(schemas[name]), title }, title, {
    additionalProperties: false,
    bannerComment: "",
  });
  write(
    name,
    `${banner}\n\n${types.replace(/\s*\/\*\*[^]*?\*\//g, "").trimStart()}`,
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
