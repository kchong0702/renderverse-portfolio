import { useContext } from "react";
import { EditingContext } from "../editing/context";
import { entryLayouts } from "../entries/layouts";
import { entryFields } from "../entries/views";
import { Section } from "../sections/section";
import { RichText } from "../text/rich-text";
import type { Block, Context, EntryKind, EntryView } from "../types";

export const EntriesBlock = ({
  block,
  ctx,
  entries = [],
}: {
  block: Block<EntryKind>;
  ctx: Context;
  entries?: EntryView[];
}) => {
  const { Entry } = useContext(EditingContext);
  const Layout = entryLayouts[ctx.spec.entry];
  return (
    <Section block={block} ctx={ctx}>
      {block.kind === "custom" && block.text && (
        <RichText path={`blocks/${block.id}/text`} value={block.text} />
      )}
      {entries.map((entry) => {
        const path = `blocks/${block.id}/items/${entry.id}`;
        return (
          <Entry
            key={entry.id}
            block={block}
            entry={entry}
            props={{
              className: "dr-entry",
              "data-layout": ctx.spec.entry,
              "data-path": path,
              children: (
                <Layout
                  entry={entry}
                  path={path}
                  fields={entryFields[block.kind]}
                />
              ),
            }}
          />
        );
      })}
    </Section>
  );
};
