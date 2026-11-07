import { describe, expect, test } from "vitest";
import { place } from "./place";
import { templates } from "../templates";
import { resume } from "../test/fixtures";

const regionsOf = (...args: Parameters<typeof place>) =>
  Object.fromEntries(
    place(...args).map(({ region, blocks }) => [
      region,
      blocks.map((block) => block.id),
    ]),
  );

describe("place", () => {
  test("blocks go to their template layout in reading order", () => {
    expect(regionsOf(resume(), templates["sidebar-band"])).toEqual({
      side: ["photo", "profile", "contacts", "sk"],
      main: ["sum", "exp"],
    });
  });

  test("the user's layout comes first and the rest follow the template layout", () => {
    const document = resume({
      design: { layouts: { "sidebar-band": { main: ["sk", "exp"] } } },
    });

    expect(regionsOf(document, templates["sidebar-band"])).toEqual({
      side: ["photo", "profile", "contacts"],
      main: ["sk", "exp", "sum"],
    });
  });

  test("blocks placed in a region the template lacks follow the template layout", () => {
    const document = resume({
      design: { layouts: { classic: { side: ["sk"] } } },
    });

    expect(regionsOf(document, templates.classic).main).toEqual([
      "sum",
      "exp",
      "sk",
    ]);
  });

  test("hidden blocks are left off", () => {
    const document = resume();
    const blocks = document.content.blocks.map((block) =>
      block.id === "sum" ? { ...block, hidden: true } : block,
    );

    expect(
      regionsOf(
        { ...document, content: { blocks } } as typeof document,
        templates.classic,
      ).main,
    ).toEqual(["exp", "sk"]);
  });

  test("the flowing region is laid out last", () => {
    expect(
      place(resume(), templates.classic).map(({ region, flows }) => [
        region,
        flows,
      ]),
    ).toEqual([
      ["top", false],
      ["main", true],
    ]);
  });
});
