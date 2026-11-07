import { readFileSync } from "node:fs";
import { expect, test } from "vitest";

test("styles use no selector Paged.js rewrites or cannot parse", () => {
  const styles = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

  expect(styles.match(/\s\+\s|:has\(|:is\(/g)).toBeNull();
});
