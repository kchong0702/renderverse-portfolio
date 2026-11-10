import type { TFunction } from "i18next";
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
import { BlockElement, Text } from "../editing/context";
import type { Contact, ContactKind } from "../generated/document";
import type { ContactsStyle } from "../generated/template";
import type { BlockProps } from "../types";

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

const ContactValue = ({
  contact,
  path,
}: {
  contact: Contact;
  path: string;
}) => {
  const href = contactHref(contact);
  const text = (
    <Text path={`${path}/${contact.id}/value`} text={contact.value.text} />
  );
  return href ? <a href={href}>{text}</a> : <span>{text}</span>;
};

const contactStyles: Record<
  ContactsStyle,
  (props: { items: Contact[]; path: string; t: TFunction }) => ReactNode
> = {
  line: ({ items, path }) => (
    <ul className="dr-contacts-line">
      {items.map((contact) => (
        <li key={contact.id}>
          <ContactValue contact={contact} path={path} />
        </li>
      ))}
    </ul>
  ),
  labelled: ({ items, path, t }) => (
    <dl className="dr-contacts-labelled">
      {items.map((contact) => (
        <div key={contact.id}>
          <dt>{contact.label?.text ?? t(`contacts.${contact.kind}`)}</dt>
          <dd>
            <ContactValue contact={contact} path={path} />
          </dd>
        </div>
      ))}
    </dl>
  ),
  "icon-tiles": ({ items, path }) => (
    <ul className="dr-contacts-tiles">
      {items.map((contact) => {
        const Icon = contactIcons[contact.kind];
        return (
          <li key={contact.id}>
            <span className="dr-tile">
              <Icon aria-hidden />
            </span>
            <ContactValue contact={contact} path={path} />
          </li>
        );
      })}
    </ul>
  ),
};

export const ContactsBlock = ({ block, ctx }: BlockProps<"contacts">) => {
  const Style = contactStyles[ctx.spec.contacts];
  return (
    <BlockElement as="div" block={block} className="dr-block dr-contacts">
      <Style items={block.items} path={`blocks/${block.id}/items`} t={ctx.t} />
    </BlockElement>
  );
};
