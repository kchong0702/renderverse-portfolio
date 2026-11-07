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
  (props: { items: Contact[]; t: TFunction }) => ReactNode
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
  labelled: ({ items, t }) => (
    <dl className="dr-contacts-labelled">
      {items.map((contact) => (
        <div key={contact.id}>
          <dt>{contact.label?.text ?? t(`contacts.${contact.kind}`)}</dt>
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

export const ContactsBlock = ({ block, ctx }: BlockProps<"contacts">) => {
  const Style = contactStyles[ctx.spec.contacts];
  return (
    <div className="dr-block dr-contacts" data-block={block.id}>
      <Style items={block.items} t={ctx.t} />
    </div>
  );
};
