import "./fonts.css";
import type { AnyDocument } from "./schema/document";
import type { TemplateSpec } from "./schema/template";
import { paginate, type Measurement } from "./paginate";

declare global {
  interface Window {
    /** Lays the document out in pages for printing and measures them */
    render: (input: {
      document: AnyDocument;
      template: TemplateSpec;
    }) => Promise<Measurement>;
  }
}

window.render = ({ document: doc, template }) =>
  paginate(
    { document: doc, template, assetUrl: (hash) => `assets/${hash}` },
    document.getElementById("pages")!,
  );
