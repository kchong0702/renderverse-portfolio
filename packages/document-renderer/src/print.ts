import "./document/fonts.css";
import type { AnyDocument } from "./generated/document";
import type { TemplateSpec } from "./generated/template";
import { paginate, type Measurement } from "./pagination/paginate";

declare global {
  interface Window {
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
