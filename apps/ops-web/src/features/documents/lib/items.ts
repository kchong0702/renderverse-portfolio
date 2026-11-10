import {
  entryFields,
  type AnyBlock,
  type Award,
  type Bullet,
  type Certification,
  type CustomEntry,
  type Date as DocumentDate,
  type Degree,
  type EntryKind,
  type Job,
  type Link,
  type Project,
  type Publication,
  type Value,
} from "@renderverse/document-renderer";

export type EntryBlock = Extract<AnyBlock, { kind: EntryKind }>;

type EntryItem = NonNullable<EntryBlock["items"]>[number];

interface EntryText {
  title: string;
  subtitle: string;
  dates: string;
}

export const INSERTS = [
  "projects",
  "certifications",
  "languages",
  "custom",
] as const;

type Insert = (typeof INSERTS)[number];

export interface NewText {
  placeholders: Record<EntryKind, EntryText>;
  entryBullet: string;
  sectionBullet: string;
  languages: string[];
  custom: { heading: string; text: string };
}

export const isEntryBlock = (block: AnyBlock): block is EntryBlock =>
  block.kind in entryFields;

export const isSection = (block: AnyBlock) =>
  !["profile", "photo", "contacts", "recipient", "letter"].includes(block.kind);

export const newId = () => crypto.randomUUID();

export const withNewIds = <T>(value: T): T =>
  JSON.parse(JSON.stringify(value), (key, field) =>
    key === "id" ? newId() : field,
  );

export const valueOf = (text: string, source: string): Value => ({
  text,
  src: [source],
});

interface EntryParts {
  id: string;
  title: Value;
  subtitle: Value | null;
  dates: DocumentDate | null;
  place: Value | null;
  bullets: Bullet[];
  links: Link[];
}

function entryOf(kind: EntryKind, parts: EntryParts): EntryItem {
  const { id, title, subtitle, dates, place, bullets, links } = parts;
  const blank = { text: "", src: [] };
  switch (kind) {
    case "experience":
      return {
        id,
        bullets,
        links,
        role: title,
        company: subtitle ?? blank,
        dates,
        location: place,
      };
    case "education":
      return {
        id,
        bullets,
        links,
        degree: title,
        school: subtitle ?? blank,
        dates,
        location: place,
      };
    case "projects":
      return { id, bullets, links, name: title, role: subtitle, dates };
    case "certifications":
      return { id, bullets, links, name: title, issuer: subtitle, date: dates };
    case "awards":
      return { id, bullets, links, title, awarder: subtitle, date: dates };
    case "publications":
      return { id, bullets, links, title, venue: subtitle, date: dates };
    case "custom":
      return { id, bullets, links, title, subtitle, dates, location: place };
  }
}

export function partsOf(item: EntryItem, kind: EntryKind): EntryParts {
  const common = {
    id: item.id,
    bullets: item.bullets ?? [],
    links: item.links ?? [],
  };
  switch (kind) {
    case "experience": {
      const job = item as Job;
      return {
        ...common,
        title: job.role,
        subtitle: job.company,
        dates: job.dates ?? null,
        place: job.location ?? null,
      };
    }
    case "education": {
      const degree = item as Degree;
      return {
        ...common,
        title: degree.degree,
        subtitle: degree.school,
        dates: degree.dates ?? null,
        place: degree.location ?? null,
      };
    }
    case "projects": {
      const project = item as Project;
      return {
        ...common,
        title: project.name,
        subtitle: project.role ?? null,
        dates: project.dates ?? null,
        place: null,
      };
    }
    case "certifications": {
      const certification = item as Certification;
      return {
        ...common,
        title: certification.name,
        subtitle: certification.issuer ?? null,
        dates: certification.date ?? null,
        place: null,
      };
    }
    case "awards": {
      const award = item as Award;
      return {
        ...common,
        title: award.title,
        subtitle: award.awarder ?? null,
        dates: award.date ?? null,
        place: null,
      };
    }
    case "publications": {
      const publication = item as Publication;
      return {
        ...common,
        title: publication.title,
        subtitle: publication.venue ?? null,
        dates: publication.date ?? null,
        place: null,
      };
    }
    case "custom": {
      const entry = item as CustomEntry;
      return {
        ...common,
        title: entry.title,
        subtitle: entry.subtitle ?? null,
        dates: entry.dates ?? null,
        place: entry.location ?? null,
      };
    }
  }
}

export const newEntry = (
  kind: EntryKind,
  text: EntryText,
  bullet: string | null,
  source: string,
): EntryItem =>
  entryOf(kind, {
    id: newId(),
    title: valueOf(text.title, source),
    subtitle: valueOf(text.subtitle, source),
    dates: { text: valueOf(text.dates, source) },
    place: null,
    bullets: bullet
      ? [{ id: newId(), text: { html: bullet, src: [source] } }]
      : [],
    links: [],
  });

export const newSection = (
  insert: Insert,
  text: NewText,
  source: string,
): AnyBlock => {
  switch (insert) {
    case "projects":
      return {
        kind: "projects",
        id: newId(),
        items: [
          newEntry(
            "projects",
            text.placeholders.projects,
            text.sectionBullet,
            source,
          ) as Project,
        ],
      };
    case "certifications":
      return {
        kind: "certifications",
        id: newId(),
        items: [
          newEntry(
            "certifications",
            text.placeholders.certifications,
            text.sectionBullet,
            source,
          ) as Certification,
        ],
      };
    case "languages":
      return {
        kind: "languages",
        id: newId(),
        items: text.languages.map((language) => ({
          id: newId(),
          language: valueOf(language, source),
        })),
      };
    case "custom":
      return {
        kind: "custom",
        id: newId(),
        heading: valueOf(text.custom.heading, source),
        text: { html: text.custom.text, src: [source] },
      };
  }
};

export const convertEntry = (
  item: EntryItem,
  from: EntryKind,
  to: EntryKind,
): EntryItem => (from === to ? item : entryOf(to, partsOf(item, from)));

export const entryAt = (blocks: AnyBlock[], path: string) => {
  const [, blockId, , itemId] = path.split("/");
  const block = blocks.find((each) => each.id === blockId);
  return block && isEntryBlock(block)
    ? {
        block,
        item: (block.items ?? []).find((each) => each.id === itemId),
      }
    : undefined;
};

export const afterFor = (
  ids: string[],
  moved: string,
  target: string,
): string | null => {
  const rest = ids.filter((id) => id !== moved);
  const index = rest.indexOf(target);
  const after = ids.includes(moved) && ids.indexOf(moved) < ids.indexOf(target);
  return after ? target : (rest[index - 1] ?? null);
};
