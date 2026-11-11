import type { ReactNode } from "react";
import type { EntryLayout } from "../generated/template";
import { EntryDetails, EntryMeta, EntryTitle } from "./details";
import type { EntryProps } from "../types";

const TitleFirst = (props: EntryProps) => (
  <>
    <div className="dr-entry-head">
      <EntryTitle {...props} />
      <EntryMeta {...props} />
    </div>
    <EntryDetails {...props} />
  </>
);

export const entryLayouts: Record<
  EntryLayout,
  (props: EntryProps) => ReactNode
> = {
  inline: TitleFirst,
  "dates-left": (props) => (
    <>
      <EntryMeta {...props} />
      <div className="dr-entry-body">
        <div className="dr-entry-head">
          <EntryTitle {...props} />
        </div>
        <EntryDetails {...props} />
      </div>
    </>
  ),
  "dates-below": TitleFirst,
};
