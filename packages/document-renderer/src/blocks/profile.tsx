import type { BlockProps } from "../types";

export const ProfileBlock = ({ block }: BlockProps<"profile">) => (
  <header className="dr-block dr-profile" data-block={block.id}>
    <h1 className="dr-name">{block.name.text}</h1>
    {block.headline && <p className="dr-headline">{block.headline.text}</p>}
  </header>
);
