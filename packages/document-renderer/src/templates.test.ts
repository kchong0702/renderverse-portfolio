import { execFileSync } from "node:child_process";
import { expect, test } from "vitest";
import { templates } from "./templates";

test("every default template matches TemplateSpec", () => {
  const checked = execFileSync(
    "uv",
    [
      "run",
      "python",
      "-c",
      "import sys; from pydantic import TypeAdapter; from document_schema import TemplateSpec; print(len(TypeAdapter(list[TemplateSpec]).validate_json(sys.stdin.read())))",
    ],
    { input: JSON.stringify(Object.values(templates)) },
  );

  expect(Number(checked)).toBe(Object.keys(templates).length);
  expect(Object.keys(templates)).toEqual(
    expect.arrayContaining(["classic", "sidebar-band"]),
  );
});
