import { Rich } from "./rich";
import { Section } from "./section";
import type { BlockProps } from "./types";

export const SummaryBlock = ({ block, ctx }: BlockProps<"summary">) => (
  <Section block={block} ctx={ctx}>
    <Rich value={block.text} />
  </Section>
);
