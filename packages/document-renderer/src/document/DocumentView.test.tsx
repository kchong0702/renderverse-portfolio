import { renderToStaticMarkup } from "react-dom/server";
import { expect, test } from "vitest";
import { DocumentView, pageCss } from "./DocumentView";
import { EditingContext, readOnly } from "../editing/context";
import { templates } from "../templates";
import { resume } from "../../tests/fixtures";

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

test("an editor gets every field's update_field path", () => {
  const out = renderToStaticMarkup(
    <EditingContext.Provider
      value={{
        ...readOnly,
        Text: ({ path, text }) => <span data-path={path}>{text}</span>,
        RichText: ({ path }) => <div data-path={path} />,
        Bullet: ({ path, bullet }) => (
          <li data-path={`${path}/bullets/${bullet.id}/text`} />
        ),
      }}
    >
      <DocumentView
        document={resume()}
        template={templates.classic}
        assetUrl={(hash) => `assets/${hash}`}
      />
    </EditingContext.Provider>,
  );

  for (const path of [
    "blocks/profile/name",
    "blocks/contacts/items/c1/value",
    "blocks/sum/heading",
    "blocks/sum/text",
    "blocks/exp/items/acme/role",
    "blocks/exp/items/acme/company",
    "blocks/exp/items/acme/dates/text",
    "blocks/exp/items/acme/bullets/b1/text",
    "blocks/sk/items/s1/label",
    "blocks/sk/items/s1/items/t1/text",
  ])
    expect(out).toContain(`data-path="${path}"`);
});
