import type { ReactNode } from "react";
import type { Skill } from "../generated/document";
import type { SkillsStyle } from "../generated/template";
import { Section } from "../sections/section";
import type { BlockProps } from "../types";

const Pills = ({ rows }: { rows: Skill[] }) =>
  rows.map((row) => (
    <div key={row.id} className="dr-skill-row">
      {row.label && <h3>{row.label.text}</h3>}
      <ul className="dr-pills">
        {row.items.map((item) => (
          <li key={item.id}>{item.text.text}</li>
        ))}
      </ul>
    </div>
  ));

const skillStyles: Record<
  SkillsStyle,
  (props: { rows: Skill[] }) => ReactNode
> = {
  inline: ({ rows }) =>
    rows.map((row) => (
      <p key={row.id} className="dr-skill-row">
        {row.label && <strong>{row.label.text}: </strong>}
        {row.items.map((item) => item.text.text).join(", ")}
      </p>
    )),
  "outline-pills": Pills,
  "filled-pills": Pills,
};

export const SkillsBlock = ({ block, ctx }: BlockProps<"skills">) => {
  const Style = skillStyles[ctx.spec.skills];
  return (
    <Section block={block} ctx={ctx}>
      <Style rows={block.items} />
    </Section>
  );
};
