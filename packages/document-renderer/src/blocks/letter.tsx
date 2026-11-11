import { BlockElement, Text } from "../editing/context";
import { RichText } from "../text/rich-text";
import type { BlockProps } from "../types";

export const LetterBlock = ({ block, ctx }: BlockProps<"letter">) => {
  const profile = ctx.document.content.blocks.find(
    (other) => other.kind === "profile",
  );
  const path = `blocks/${block.id}`;
  return (
    <BlockElement as="div" block={block} className="dr-block dr-letter">
      {block.date && (
        <p className="dr-letter-date">
          <Text path={`${path}/date`} text={block.date.text} />
        </p>
      )}
      {block.subject && (
        <p className="dr-letter-subject">
          <Text path={`${path}/subject`} text={block.subject.text} />
        </p>
      )}
      <p>
        <Text path={`${path}/greeting`} text={block.greeting.text} />
      </p>
      {block.paragraphs.map((paragraph) => (
        <RichText
          key={paragraph.id}
          path={`${path}/paragraphs/${paragraph.id}/text`}
          value={paragraph.text}
        />
      ))}
      <p className="dr-letter-closing">
        <Text path={`${path}/closing`} text={block.closing.text} />
      </p>
      {block.signature && (
        <img
          className="dr-signature"
          src={ctx.assetUrl(block.signature)}
          alt=""
        />
      )}
      {profile && <p className="dr-letter-name">{profile.name.text}</p>}
    </BlockElement>
  );
};
