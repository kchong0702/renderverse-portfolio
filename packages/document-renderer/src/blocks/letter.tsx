import { Rich } from "./rich";
import type { BlockProps } from "./types";

export const LetterBlock = ({ block, ctx }: BlockProps<"letter">) => {
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
};
