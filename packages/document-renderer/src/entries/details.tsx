import { useContext } from "react";
import { EditingContext, Text } from "../editing/context";
import { RichText } from "../text/rich-text";
import type { EntryProps } from "../types";

export const EntryTitle = ({ entry, path, fields }: EntryProps) => (
  <div className="dr-entry-what">
    <strong>
      <Text path={`${path}/${fields.title}`} text={entry.title} />
    </strong>
    {entry.subtitle && (
      <span className="dr-entry-sub">
        <Text path={`${path}/${fields.subtitle}`} text={entry.subtitle} />
      </span>
    )}
  </div>
);

export const EntryMeta = ({ entry, path, fields }: EntryProps) =>
  (entry.dates || entry.place) && (
    <div className="dr-entry-when">
      {entry.dates && (
        <span>
          <Text path={`${path}/${fields.dates}/text`} text={entry.dates} />
        </span>
      )}
      {entry.place && (
        <span>
          <Text path={`${path}/${fields.place}`} text={entry.place} />
        </span>
      )}
    </div>
  );

export const EntryDetails = ({ entry, path }: EntryProps) => {
  const { Bullet } = useContext(EditingContext);
  return (
    <>
      {entry.note && <p className="dr-entry-note">{entry.note}</p>}
      {entry.text && (
        <RichText path={`${path}/description`} value={entry.text} />
      )}
      {!!entry.bullets?.length && (
        <ul className="dr-bullets">
          {entry.bullets.map((bullet) => (
            <Bullet key={bullet.id} path={path} bullet={bullet} />
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
};
