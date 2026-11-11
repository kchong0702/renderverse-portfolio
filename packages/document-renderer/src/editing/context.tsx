import {
  createContext,
  useContext,
  type ComponentType,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import type { Bullet, RichValue } from "../generated/document";
import type { Region } from "../generated/template";
import type { AnyBlock } from "../layout/place";
import type { Block, EntryKind, EntryView } from "../types";

export type ElementProps = HTMLAttributes<HTMLElement> & {
  [attribute: `data-${string}`]: string | boolean | undefined;
};

export type BlockTag = "header" | "figure" | "div" | "section" | "address";

export interface Editing {
  Region: ComponentType<{ region: Region; props: ElementProps }>;
  BlockRoot: ComponentType<{
    as: BlockTag;
    block: AnyBlock;
    props: ElementProps;
  }>;
  Entry: ComponentType<{
    block: Block<EntryKind>;
    entry: EntryView;
    props: ElementProps;
  }>;
  Bullet: ComponentType<{ path: string; bullet: Bullet }>;
  Text: ComponentType<{ path: string; text: string; item?: string }>;
  RichText: ComponentType<{ path: string; value: RichValue }>;
  AddSkill: ComponentType<{ parent: string; after: string | null }>;
}

export const readOnly: Editing = {
  Region: ({ props }) => <section {...props} />,
  BlockRoot: ({ as: Tag, props }) => <Tag {...props} />,
  Entry: ({ props }) => <article {...props} />,
  Bullet: ({ bullet }) => (
    <li dangerouslySetInnerHTML={{ __html: bullet.text.html }} />
  ),
  Text: ({ text }): ReactNode => text,
  RichText: ({ value }) => (
    <div
      className="dr-rich"
      style={value.align ? { textAlign: value.align } : undefined}
      dangerouslySetInnerHTML={{ __html: value.html }}
    />
  ),
  AddSkill: () => null,
};

export const EditingContext = createContext<Editing>(readOnly);

export const BlockElement = ({
  as,
  block,
  className,
  ...props
}: ElementProps & { as: BlockTag; block: AnyBlock }) => {
  const { BlockRoot } = useContext(EditingContext);
  return (
    <BlockRoot
      as={as}
      block={block}
      props={{ className, "data-block": block.id, ...props }}
    />
  );
};

export const Text = (props: { path: string; text: string; item?: string }) => {
  const { Text: Slot } = useContext(EditingContext);
  return <Slot {...props} />;
};

export const AddSkill = (props: { parent: string; after: string | null }) => {
  const { AddSkill: Slot } = useContext(EditingContext);
  return <Slot {...props} />;
};
