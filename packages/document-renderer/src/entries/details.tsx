import { RichText } from "../text/rich-text";
import type { EntryView } from "../types";

export const EntryTitle = ({ entry }: { entry: EntryView }) => (
  <div className="dr-entry-what">
    <strong>{entry.title}</strong>
    {entry.subtitle && <span className="dr-entry-sub">{entry.subtitle}</span>}
  </div>
);

export const EntryMeta = ({ entry }: { entry: EntryView }) =>
  (entry.dates || entry.place) && (
    <div className="dr-entry-when">
      {entry.dates && <span>{entry.dates}</span>}
      {entry.place && <span>{entry.place}</span>}
    </div>
  );

export const EntryDetails = ({ entry }: { entry: EntryView }) => (
  <>
    {entry.note && <p className="dr-entry-note">{entry.note}</p>}
    {entry.text && <RichText value={entry.text} />}
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
