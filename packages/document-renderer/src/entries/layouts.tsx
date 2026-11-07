import type { ReactNode } from "react";
import type { EntryLayout } from "../generated/template";
import { EntryDetails, EntryMeta, EntryTitle } from "./details";
import type { EntryView } from "../types";

const TitleFirst = ({ entry }: { entry: EntryView }) => (
  <>
    <div className="dr-entry-head">
      <EntryTitle entry={entry} />
      <EntryMeta entry={entry} />
    </div>
    <EntryDetails entry={entry} />
  </>
);

export const entryLayouts: Record<
  EntryLayout,
  (props: { entry: EntryView }) => ReactNode
> = {
  inline: TitleFirst,
  "dates-left": ({ entry }) => (
    <>
      <EntryMeta entry={entry} />
      <div className="dr-entry-body">
        <div className="dr-entry-head">
          <EntryTitle entry={entry} />
        </div>
        <EntryDetails entry={entry} />
      </div>
    </>
  ),
  "dates-below": TitleFirst,
};
