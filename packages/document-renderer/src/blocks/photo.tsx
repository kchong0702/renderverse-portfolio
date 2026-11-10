import type { BlockProps } from "../types";

export const PhotoBlock = ({ block, ctx }: BlockProps<"photo">) => (
  <figure
    className="dr-block dr-photo"
    data-block={block.id}
    data-spot={ctx.photo}
    data-ring={ctx.spec.photo_ring}
  >
    <img src={ctx.assetUrl(block.file)} alt="" />
  </figure>
);
