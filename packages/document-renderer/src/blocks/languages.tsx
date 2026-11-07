import { Section } from "./section";
import type { BlockProps } from "./types";

export const LanguagesBlock = ({ block, ctx }: BlockProps<"languages">) => (
  <Section block={block} ctx={ctx}>
    <ul className="dr-languages">
      {block.items.map((item) => (
        <li key={item.id}>
          <strong>{item.language.text}</strong>
          {item.fluency && <span>{item.fluency.text}</span>}
        </li>
      ))}
    </ul>
  </Section>
);
