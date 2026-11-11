import { BlockElement, Text } from "../editing/context";
import type { BlockProps } from "../types";

export const RecipientBlock = ({ block }: BlockProps<"recipient">) => (
  <BlockElement as="address" block={block} className="dr-block dr-recipient">
    {(["name", "title", "organization"] as const).map(
      (field) =>
        block[field] && (
          <span key={field}>
            <Text
              path={`blocks/${block.id}/${field}`}
              text={block[field].text}
            />
          </span>
        ),
    )}
    {block.address?.map((line, index) => (
      <span key={index}>{line.text}</span>
    ))}
  </BlockElement>
);
