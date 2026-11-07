import type { ReactNode } from "react";
import type { EntryLayout } from "../generated/template";
import { Details, What, When } from "./details";
import { Rich } from "./rich";
import { Section } from "./section";
import type { Block, Context, EntryKind, EntryView } from "./types";

const HeadFirst = ({ entry }: { entry: EntryView }) => (
  <>
    <div className="dr-entry-head">
      <What entry={entry} />
      <When entry={entry} />
    </div>
    <Details entry={entry} />
  </>
);

const entryLayouts: Record<
  EntryLayout,
  (props: { entry: EntryView }) => ReactNode
> = {
  inline: HeadFirst,
  "dates-left": ({ entry }) => (
    <>
      <When entry={entry} />
      <div className="dr-entry-body">
        <div className="dr-entry-head">
          <What entry={entry} />
        </div>
        <Details entry={entry} />
      </div>
    </>
  ),
  "dates-below": HeadFirst,
};

export const Entries = ({
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
      {block.kind === "custom" && block.text && <Rich value={block.text} />}
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
