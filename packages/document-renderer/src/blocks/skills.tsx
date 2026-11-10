import { Fragment, type ReactNode } from "react";
import { Text } from "../editing/context";
import type { Skill } from "../generated/document";
import type { SkillsStyle } from "../generated/template";
import { Section } from "../sections/section";
import type { BlockProps } from "../types";

const Pills = ({ rows, path }: { rows: Skill[]; path: string }) =>
  rows.map((row) => (
    <div key={row.id} className="dr-skill-row">
      {row.label && (
        <h3>
          <Text path={`${path}/${row.id}/label`} text={row.label.text} />
        </h3>
      )}
      <ul className="dr-pills">
        {row.items.map((item) => (
          <li key={item.id}>
            <Text
              path={`${path}/${row.id}/items/${item.id}/text`}
              text={item.text.text}
            />
          </li>
        ))}
      </ul>
    </div>
  ));

const skillStyles: Record<
  SkillsStyle,
  (props: { rows: Skill[]; path: string }) => ReactNode
> = {
  inline: ({ rows, path }) =>
    rows.map((row) => (
      <p key={row.id} className="dr-skill-row">
        {row.label && (
          <strong>
            <Text path={`${path}/${row.id}/label`} text={row.label.text} />
            {": "}
          </strong>
        )}
        {row.items.map((item, index) => (
          <Fragment key={item.id}>
            {index > 0 && ", "}
            <Text
              path={`${path}/${row.id}/items/${item.id}/text`}
              text={item.text.text}
            />
          </Fragment>
        ))}
      </p>
    )),
  "outline-pills": Pills,
  "filled-pills": Pills,
};

export const SkillsBlock = ({ block, ctx }: BlockProps<"skills">) => {
  const Style = skillStyles[ctx.spec.skills];
  return (
    <Section block={block} ctx={ctx}>
      <Style rows={block.items} path={`blocks/${block.id}/items`} />
    </Section>
  );
};
