import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import {
  FaEnvelope,
  FaGithub,
  FaGlobe,
  FaLink,
  FaLinkedinIn,
  FaLocationDot,
  FaPhone,
} from "react-icons/fa6";
import type { AnyBlock, Spec } from "./layout";
import type {
  AnyDocument,
  Bullet,
  Contact,
  ContactKind,
  Date,
  Link,
  RichValue,
  Skill,
} from "./schema/document";
import type {
  ContactsStyle,
  EntryLayout,
  PhotoSpot,
  SkillsStyle,
} from "./schema/template";
import { textFor, type SectionKind } from "./text";

export interface Context {
  document: AnyDocument;
  spec: Spec;
  photo: PhotoSpot;
  assetUrl: (hash: string) => string;
}

type Block<K extends AnyBlock["kind"]> = Extract<AnyBlock, { kind: K }>;

interface EntryView {
  id: string;
  title: string;
  subtitle?: string;
  dates?: string;
  place?: string;
  note?: string;
  text?: RichValue | null;
  bullets?: Bullet[];
  links?: Link[];
  tags?: string[];
}

type EntrySection = Block<
  | "experience"
  | "education"
  | "projects"
  | "certifications"
  | "awards"
  | "publications"
  | "custom"
>;

const date = (value?: Date | null) => value?.text.text;

const entryViews: {
  [K in EntrySection["kind"]]: (
    item: NonNullable<Block<K>["items"]>[number],
  ) => EntryView;
} = {
  experience: (job) => ({
    ...job,
    title: job.role.text,
    subtitle: job.company.text,
    dates: date(job.dates),
    place: job.location?.text,
    text: job.description,
  }),
  education: (degree) => ({
    ...degree,
    title: degree.degree.text,
    subtitle: degree.school.text,
    dates: date(degree.dates),
    place: degree.location?.text,
    note: degree.grade?.text,
  }),
  projects: (project) => ({
    ...project,
    title: project.name.text,
    subtitle: project.role?.text,
    dates: date(project.dates),
    text: project.description,
    tags: project.tags?.map((tag) => tag.text.text),
  }),
  certifications: (item) => ({
    ...item,
    title: item.name.text,
    subtitle: item.issuer?.text,
    dates: date(item.date),
  }),
  awards: (item) => ({
    ...item,
    title: item.title.text,
    subtitle: item.awarder?.text,
    dates: date(item.date),
  }),
  publications: (item) => ({
    ...item,
    title: item.title.text,
    subtitle: item.venue?.text,
    dates: date(item.date),
    note: [
      item.authors?.map((author) => author.text).join(", "),
      item.doi && `doi:${item.doi.text}`,
    ]
      .filter(Boolean)
      .join(" · "),
  }),
  custom: (item) => ({
    ...item,
    title: item.title.text,
    subtitle: item.subtitle?.text,
    dates: date(item.dates),
    place: item.location?.text,
  }),
};

const Rich = ({ value }: { value: RichValue }) => (
  <div
    className="dr-rich"
    style={value.align ? { textAlign: value.align } : undefined}
    dangerouslySetInnerHTML={{ __html: value.html }}
  />
);

const What = ({ entry }: { entry: EntryView }) => (
  <div className="dr-entry-what">
    <strong>{entry.title}</strong>
    {entry.subtitle && <span className="dr-entry-sub">{entry.subtitle}</span>}
  </div>
);

const When = ({ entry }: { entry: EntryView }) =>
  (entry.dates || entry.place) && (
    <div className="dr-entry-when">
      {entry.dates && <span>{entry.dates}</span>}
      {entry.place && <span>{entry.place}</span>}
    </div>
  );

const Details = ({ entry }: { entry: EntryView }) => (
  <>
    {entry.note && <p className="dr-entry-note">{entry.note}</p>}
    {entry.text && <Rich value={entry.text} />}
    {!!entry.bullets?.length && (
      <ul className="dr-bullets">
        {entry.bullets.map((bullet) => (
          <li
            key={bullet.id}
            dangerouslySetInnerHTML={{ __html: bullet.text.html }}
          />
        ))}
      </ul>
    )}
    {!!entry.tags?.length && (
      <p className="dr-entry-tags">{entry.tags.join(" · ")}</p>
    )}
    {!!entry.links?.length && (
      <p className="dr-entry-links">
        {entry.links.map((link) => (
          <a key={link.id} href={link.url.text}>
            {link.label?.text ?? link.url.text}
          </a>
        ))}
      </p>
    )}
  </>
);

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

const contactIcons: Record<ContactKind, IconType> = {
  email: FaEnvelope,
  phone: FaPhone,
  location: FaLocationDot,
  linkedin: FaLinkedinIn,
  github: FaGithub,
  website: FaGlobe,
  other: FaLink,
};

const contactHref = ({ kind, value: { text } }: Contact) =>
  ({
    email: `mailto:${text}`,
    phone: `tel:${text.replace(/[^\d+]/g, "")}`,
    location: undefined,
    linkedin: text.startsWith("http") ? text : `https://${text}`,
    github: text.startsWith("http") ? text : `https://${text}`,
    website: text.startsWith("http") ? text : `https://${text}`,
    other: text.startsWith("http") ? text : undefined,
  })[kind];

const ContactValue = ({ contact }: { contact: Contact }) => {
  const href = contactHref(contact);
  return href ? (
    <a href={href}>{contact.value.text}</a>
  ) : (
    <span>{contact.value.text}</span>
  );
};

const contactStyles: Record<
  ContactsStyle,
  (props: { items: Contact[]; language?: string }) => ReactNode
> = {
  line: ({ items }) => (
    <ul className="dr-contacts-line">
      {items.map((contact) => (
        <li key={contact.id}>
          <ContactValue contact={contact} />
        </li>
      ))}
    </ul>
  ),
  labelled: ({ items, language }) => (
    <dl className="dr-contacts-labelled">
      {items.map((contact) => (
        <div key={contact.id}>
          <dt>
            {contact.label?.text ?? textFor(language).contacts[contact.kind]}
          </dt>
          <dd>
            <ContactValue contact={contact} />
          </dd>
        </div>
      ))}
    </dl>
  ),
  "icon-tiles": ({ items }) => (
    <ul className="dr-contacts-tiles">
      {items.map((contact) => {
        const Icon = contactIcons[contact.kind];
        return (
          <li key={contact.id}>
            <span className="dr-tile">
              <Icon aria-hidden />
            </span>
            <ContactValue contact={contact} />
          </li>
        );
      })}
    </ul>
  ),
};

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

const Section = ({
  block,
  ctx,
  children,
}: {
  block: Block<SectionKind>;
  ctx: Context;
  children: ReactNode;
}) => (
  <section
    className="dr-block dr-section"
    data-block={block.id}
    data-kind={block.kind}
  >
    <h2 className="dr-title">
      <span>
        {block.heading?.text ??
          textFor(ctx.document.language).headings[block.kind]}
      </span>
    </h2>
    {children}
  </section>
);

const Entries = ({ block, ctx }: { block: EntrySection; ctx: Context }) => {
  const Layout = entryLayouts[ctx.spec.entry];
  const view = entryViews[block.kind] as (
    item: NonNullable<EntrySection["items"]>[number],
  ) => EntryView;
  return (
    <Section block={block} ctx={ctx}>
      {block.kind === "custom" && block.text && <Rich value={block.text} />}
      {block.items?.map((item) => (
        <article
          key={item.id}
          className="dr-entry"
          data-layout={ctx.spec.entry}
          data-path={`blocks/${block.id}/items/${item.id}`}
        >
          <Layout entry={view(item)} />
        </article>
      ))}
    </Section>
  );
};

export const blocks: {
  [K in AnyBlock["kind"]]: (props: {
    block: Block<K>;
    ctx: Context;
  }) => ReactNode;
} = {
  profile: ({ block }) => (
    <header className="dr-block dr-profile" data-block={block.id}>
      <h1 className="dr-name">{block.name.text}</h1>
      {block.headline && <p className="dr-headline">{block.headline.text}</p>}
    </header>
  ),
  photo: ({ block, ctx }) => (
    <figure
      className="dr-block dr-photo"
      data-block={block.id}
      data-spot={ctx.photo}
      data-ring={ctx.spec.photo_ring}
    >
      <img src={ctx.assetUrl(block.file)} alt="" />
    </figure>
  ),
  contacts: ({ block, ctx }) => {
    const Style = contactStyles[ctx.spec.contacts];
    return (
      <div className="dr-block dr-contacts" data-block={block.id}>
        <Style items={block.items} language={ctx.document.language} />
      </div>
    );
  },
  summary: ({ block, ctx }) => (
    <Section block={block} ctx={ctx}>
      <Rich value={block.text} />
    </Section>
  ),
  skills: ({ block, ctx }) => {
    const Style = skillStyles[ctx.spec.skills];
    return (
      <Section block={block} ctx={ctx}>
        <Style rows={block.items} />
      </Section>
    );
  },
  languages: ({ block, ctx }) => (
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
  ),
  experience: Entries,
  education: Entries,
  projects: Entries,
  certifications: Entries,
  awards: Entries,
  publications: Entries,
  custom: Entries,
  recipient: ({ block }) => (
    <address className="dr-block dr-recipient" data-block={block.id}>
      {[
        block.name,
        block.title,
        block.organization,
        ...(block.address ?? []),
      ].map((line, index) => line && <span key={index}>{line.text}</span>)}
    </address>
  ),
  letter: ({ block, ctx }) => {
    const profile = ctx.document.content.blocks.find(
      (other) => other.kind === "profile",
    );
    return (
      <div className="dr-block dr-letter" data-block={block.id}>
        {block.date && <p className="dr-letter-date">{block.date.text}</p>}
        {block.subject && (
          <p className="dr-letter-subject">{block.subject.text}</p>
        )}
        <p>{block.greeting.text}</p>
        {block.paragraphs.map((paragraph) => (
          <Rich key={paragraph.id} value={paragraph.text} />
        ))}
        <p className="dr-letter-closing">{block.closing.text}</p>
        {block.signature && (
          <img
            className="dr-signature"
            src={ctx.assetUrl(block.signature)}
            alt=""
          />
        )}
        {profile && <p className="dr-letter-name">{profile.name.text}</p>}
      </div>
    );
  },
};
