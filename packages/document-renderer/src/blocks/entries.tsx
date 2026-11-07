import { entryLayouts } from "../entries/layouts";
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
  const Layout = entryLayouts[ctx.spec.entry];
  return (
    <Section block={block} ctx={ctx}>
      {block.kind === "custom" && block.text && <RichText value={block.text} />}
      {entries.map((entry) => (
        <article
          key={entry.id}
          className="dr-entry"
          data-layout={ctx.spec.entry}
          data-path={`blocks/${block.id}/items/${entry.id}`}
        >
          <Layout entry={entry} />
        </article>
      ))}
    </Section>
  );
};
