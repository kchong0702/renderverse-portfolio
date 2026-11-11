import type { AnyBlock, TemplateSpec } from "@renderverse/document-renderer";
import type { TFunction } from "i18next";
import { createContext, useContext } from "react";
import type { DocumentRecord, Edit } from "../../api/documents";
import { replaceTemplateLayout, type Arrangement } from "../../lib/arrangement";

export interface Page {
  record: DocumentRecord;
  template: TemplateSpec;
  arrangement: Arrangement;
  source: string;
  edit: (edits: Edit[]) => void;
}

export const PageContext = createContext<Page | null>(null);

export const usePage = () => useContext(PageContext)!;

export const arrange = (page: Page, arrangement: Arrangement) =>
  page.edit([
    {
      kind: "update_design",
      design: replaceTemplateLayout(
        page.record.body.design,
        page.template.id,
        arrangement,
      ),
    },
  ]);

export const blockLabel = (block: AnyBlock, t: TFunction) =>
  ("heading" in block && block.heading?.text) ||
  t(`documents.blocks.${block.kind}`);
