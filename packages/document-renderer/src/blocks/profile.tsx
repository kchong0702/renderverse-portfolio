import { BlockElement, Text } from "../editing/context";
import type { BlockProps } from "../types";

export const ProfileBlock = ({ block }: BlockProps<"profile">) => (
  <BlockElement as="header" block={block} className="dr-block dr-profile">
    <h1 className="dr-name">
      <Text path={`blocks/${block.id}/name`} text={block.name.text} />
    </h1>
    {block.headline && (
      <p className="dr-headline">
        <Text path={`blocks/${block.id}/headline`} text={block.headline.text} />
      </p>
    )}
  </BlockElement>
);
