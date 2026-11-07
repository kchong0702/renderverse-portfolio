import type { BlockProps } from "../types";

export const RecipientBlock = ({ block }: BlockProps<"recipient">) => (
  <address className="dr-block dr-recipient" data-block={block.id}>
    {[
      block.name,
      block.title,
      block.organization,
      ...(block.address ?? []),
    ].map((line, index) => line && <span key={index}>{line.text}</span>)}
  </address>
);
