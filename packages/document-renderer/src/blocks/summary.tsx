import { RichText } from "../text/rich-text";
import { Section } from "../sections/section";
import type { BlockProps } from "../types";

export const SummaryBlock = ({ block, ctx }: BlockProps<"summary">) => (
  <Section block={block} ctx={ctx}>
    <RichText path={`blocks/${block.id}/text`} value={block.text} />
  </Section>
);
