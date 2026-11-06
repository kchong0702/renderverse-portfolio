import { Previewer } from "pagedjs";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import {
  DocumentView,
  PAGE_MM,
  designOf,
  pageCss,
  type DocumentViewProps,
} from "./DocumentView";
import type { RegionOverflow, Report } from "./schema/report";
import type { Region } from "./schema/template";
import styles from "./styles.css?inline";

export type Measurement = Omit<Report, "render_id">;

const PX_PER_MM = 96 / 25.4;

const bottomOf = (element: Element) =>
  Math.max(
    element.getBoundingClientRect().bottom,
    ...[...element.querySelectorAll("*")].map(
      (child) => child.getBoundingClientRect().bottom,
    ),
  );

/** Lays the document out off screen and caps each region that must fit on the first page */
async function capRegions(
  html: string,
  props: DocumentViewProps,
): Promise<{ html: string; overflows: RegionOverflow[] }> {
  const design = designOf(props.document);
  const [width, height] = PAGE_MM[design.page_size];
  const room = (height - 2 * design.margins_mm) * PX_PER_MM;
  const probe = document.createElement("div");
  probe.style.cssText = `position: absolute; left: -10000px; top: 0; width: ${width}mm`;
  probe.innerHTML = `<style>${styles}</style>${html}`;
  document.body.append(probe);
  await Promise.all(
    [...probe.querySelectorAll("img")].map((image) =>
      image.decode().catch(() => undefined),
    ),
  );
  // Lays the probe out so its fonts start loading before the wait
  probe.getBoundingClientRect();
  await document.fonts.ready;

  const page = probe.querySelector(".dr-page")!;
  const top = page.getBoundingClientRect().top;
  const overflows: RegionOverflow[] = [];
  for (const region of probe.querySelectorAll<HTMLElement>(
    '.dr-region[data-flows="false"]',
  )) {
    const start = region.getBoundingClientRect().top;
    const over =
      Math.max(start, ...[...region.children].map(bottomOf)) - top - room;
    if (over > 0.5) {
      overflows.push({
        kind: "region_overflow",
        region: region.dataset.region as Region,
        by_mm: Math.round((over / PX_PER_MM) * 10) / 10,
      });
      region.style.maxHeight = `${(room - start + top) / PX_PER_MM}mm`;
      region.style.overflow = "hidden";
    }
  }
  const capped = page.outerHTML;
  probe.remove();
  return { html: capped, overflows };
}

/** Splits the document into pages inside target with Paged.js and measures the result */
export async function paginate(
  props: DocumentViewProps,
  target: HTMLElement,
): Promise<Measurement> {
  const { html, overflows } = await capRegions(
    renderToStaticMarkup(createElement(DocumentView, props)),
    props,
  );
  await new Previewer().preview(
    html,
    [
      {
        [location.href]: `${styles}\n${pageCss(props.document, props.template)}`,
      },
    ],
    target,
  );

  const pages = [...target.querySelectorAll<HTMLElement>(".pagedjs_page")];
  const spans = new Map<string, [number, number]>();
  const entries = new Map<string, [number, number]>();
  const warnings: Measurement["warnings"] = [...overflows];
  const extend = (
    seen: Map<string, [number, number]>,
    key: string,
    page: number,
  ) => seen.set(key, [seen.get(key)?.[0] ?? page, page]);

  pages.forEach((page, index) => {
    page
      .querySelectorAll<HTMLElement>("[data-block]")
      .forEach((block) => extend(spans, block.dataset.block!, index + 1));
    page
      .querySelectorAll<HTMLElement>("[data-path]")
      .forEach((entry) => extend(entries, entry.dataset.path!, index + 1));
    page.querySelectorAll<HTMLElement>(".dr-section").forEach((section) => {
      const title = section.querySelector(".dr-title");
      if (
        title &&
        section.textContent?.trim() === title.textContent?.trim() &&
        index < pages.length - 1
      ) {
        warnings.push({
          kind: "orphan_heading",
          block: section.dataset.block!,
          page: index + 1,
        });
      }
    });
  });
  for (const [path, [first, last]] of entries) {
    if (last > first)
      warnings.push({ kind: "split_entry", path, pages: [first, last] });
  }

  const last = pages.at(-1)!;
  const area = last.querySelector(".pagedjs_area")!.getBoundingClientRect();
  const blocks = [...last.querySelectorAll("[data-block]")];
  const fill = blocks.length
    ? (Math.max(...blocks.map(bottomOf)) - area.top) / area.height
    : 0;

  return {
    pages: pages.length,
    last_page_fill: Math.min(1, Math.max(0, Math.round(fill * 1000) / 1000)),
    spans: [...spans].map(([block, [first_page, last_page]]) => ({
      block,
      first_page,
      last_page,
    })),
    warnings,
  };
}
