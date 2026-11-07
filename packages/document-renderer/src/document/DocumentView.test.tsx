import { renderToStaticMarkup } from "react-dom/server";
import { expect, test } from "vitest";
import { DocumentView, pageCss } from "./DocumentView";
import { templates } from "../templates";
import { resume } from "../test/fixtures";

const html = (document = resume(), template = templates["sidebar-band"]) =>
  renderToStaticMarkup(
    <DocumentView
      document={document}
      template={template}
      assetUrl={(hash) => `assets/${hash}`}
    />,
  );

test("each region carries the variants its blocks follow", () => {
  expect(html()).toContain(
    'data-region="side" data-flows="false" data-band="true" data-fill="accent"',
  );
  expect(html()).toMatch(/<dl class="dr-contacts-labelled">.*<dt>Email<\/dt>/);
  expect(html()).toContain(
    'data-layout="dates-left" data-path="blocks/exp/items/acme"',
  );
});

test("the design overrides the template's accent and font", () => {
  const out = html(
    resume({ design: { accent: "#AA0000", font: "eb-garamond" } }),
  );

  expect(out).toContain("--accent:#AA0000");
  expect(out).toContain("--heading-font:&quot;EB Garamond&quot;, serif");
});

test("default headings follow the document's language", () => {
  expect(html(resume({ language: "ms-MY" }))).toContain(
    "<span>Pengalaman</span>",
  );
});

test("a band down the page is painted on every page at its columns", () => {
  expect(pageCss(resume(), templates["sidebar-band"])).toBe(
    [
      "@page { size: A4; margin: 16mm 0; }",
      ".pagedjs_page { background: linear-gradient(to right, transparent 0mm, #1F4E79 0mm, #1F4E79 74.33mm, transparent 74.33mm); }",
    ].join("\n"),
  );
});

test("a template without a photo spot leaves the photo off", () => {
  expect(html(resume(), { ...templates.classic, photo: "none" })).not.toContain(
    "dr-photo",
  );
});
