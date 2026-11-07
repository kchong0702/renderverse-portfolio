import type { ReactNode } from "react";
import type { Block, Context, SectionKind } from "./types";

export const Section = ({
  block,
  ctx,
  children,
}: {
  block: Block<SectionKind>;
  ctx: Context;
  children: ReactNode;
}) => (
  <section
    className="dr-block dr-section"
    data-block={block.id}
    data-kind={block.kind}
  >
    <h2 className="dr-title">
      <span>{block.heading?.text ?? ctx.t(`headings.${block.kind}`)}</span>
    </h2>
    {children}
  </section>
);
