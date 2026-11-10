import { Text } from "../editing/context";
import { Section } from "../sections/section";
import type { BlockProps } from "../types";

export const LanguagesBlock = ({ block, ctx }: BlockProps<"languages">) => (
  <Section block={block} ctx={ctx}>
    <ul className="dr-languages">
      {block.items.map((item) => (
        <li key={item.id}>
          <strong>
            <Text
              path={`blocks/${block.id}/items/${item.id}/language`}
              text={item.language.text}
            />
          </strong>
          {item.fluency && (
            <span>
              <Text
                path={`blocks/${block.id}/items/${item.id}/fluency`}
                text={item.fluency.text}
              />
            </span>
          )}
        </li>
      ))}
    </ul>
  </Section>
);
