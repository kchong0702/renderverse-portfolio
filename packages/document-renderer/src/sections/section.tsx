import type { ReactNode } from "react";
import { BlockElement, Text } from "../editing/context";
import type { Block, Context, SectionKind } from "../types";

export const Section = ({
  block,
  ctx,
  children,
}: {
  block: Block<SectionKind>;
  ctx: Context;
  children: ReactNode;
}) => (
  <BlockElement
    as="section"
    block={block}
    className="dr-block dr-section"
    data-kind={block.kind}
  >
    <h2 className="dr-title">
      <span>
        <Text
          path={`blocks/${block.id}/heading`}
          text={block.heading?.text ?? ctx.t(`headings.${block.kind}`)}
        />
      </span>
    </h2>
    {children}
  </BlockElement>
);
