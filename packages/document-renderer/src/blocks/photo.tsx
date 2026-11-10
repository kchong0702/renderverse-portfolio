import { BlockElement } from "../editing/context";
import type { BlockProps } from "../types";

export const PhotoBlock = ({ block, ctx }: BlockProps<"photo">) => (
  <BlockElement
    as="figure"
    block={block}
    className="dr-block dr-photo"
    data-spot={ctx.photo}
    data-ring={ctx.spec.photo_ring}
  >
    <img src={ctx.assetUrl(block.file)} alt="" />
  </BlockElement>
);
