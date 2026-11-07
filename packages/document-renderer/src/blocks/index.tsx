import type { ReactNode } from "react";
import type { AnyBlock } from "../layout/place";
import { ContactsBlock } from "./contacts";
import { Entries } from "./entries";
import { entryViews } from "./entry-views";
import { LanguagesBlock } from "./languages";
import { LetterBlock } from "./letter";
import { PhotoBlock } from "./photo";
import { ProfileBlock } from "./profile";
import { RecipientBlock } from "./recipient";
import { SkillsBlock } from "./skills";
import { SummaryBlock } from "./summary";
import type { BlockProps } from "./types";

export type { Context } from "./types";

export const blocks: {
  [K in AnyBlock["kind"]]: (props: BlockProps<K>) => ReactNode;
} = {
  profile: ProfileBlock,
  photo: PhotoBlock,
  contacts: ContactsBlock,
  summary: SummaryBlock,
  skills: SkillsBlock,
  languages: LanguagesBlock,
  experience: ({ block, ctx }) => (
    <Entries
      block={block}
      ctx={ctx}
      entries={block.items?.map(entryViews.experience)}
    />
  ),
  education: ({ block, ctx }) => (
    <Entries
      block={block}
      ctx={ctx}
      entries={block.items?.map(entryViews.education)}
    />
  ),
  projects: ({ block, ctx }) => (
    <Entries
      block={block}
      ctx={ctx}
      entries={block.items?.map(entryViews.projects)}
    />
  ),
  certifications: ({ block, ctx }) => (
    <Entries
      block={block}
      ctx={ctx}
      entries={block.items?.map(entryViews.certifications)}
    />
  ),
  awards: ({ block, ctx }) => (
    <Entries
      block={block}
      ctx={ctx}
      entries={block.items?.map(entryViews.awards)}
    />
  ),
  publications: ({ block, ctx }) => (
    <Entries
      block={block}
      ctx={ctx}
      entries={block.items?.map(entryViews.publications)}
    />
  ),
  custom: ({ block, ctx }) => (
    <Entries
      block={block}
      ctx={ctx}
      entries={block.items?.map(entryViews.custom)}
    />
  ),
  recipient: RecipientBlock,
  letter: LetterBlock,
};
