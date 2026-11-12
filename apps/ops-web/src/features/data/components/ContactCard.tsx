import { Pencil, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  useUpdateProfile,
  type Profile,
  type ProfileLink,
} from "@/features/portfolio";
import { buttonClass } from "@/shared/components/button";
import { TextAreaField, TextField } from "@/shared/components/fields";
import { cn } from "@/shared/lib/cn";
import { useCopied } from "../hooks/useCopied";
import { shortUrl } from "../lib/facts";
import CopyIconButton from "./CopyIconButton";
import Section from "./Section";

interface ContactFormProps {
  profile: Profile;
  onDone: () => void;
}

function ContactForm({ profile, onDone }: ContactFormProps) {
  const { t } = useTranslation();
  const update = useUpdateProfile();
  const [draft, setDraft] = useState(profile);
  const [links, setLinks] = useState<ProfileLink[]>(profile.links);
  const set = (change: Partial<Profile>) =>
    setDraft((current) => ({ ...current, ...change }));
  const setLink = (index: number, change: Partial<ProfileLink>) =>
    setLinks((current) =>
      current.map((link, at) => (at === index ? { ...link, ...change } : link)),
    );

  const submit = (event: FormEvent) => {
    event.preventDefault();
    update.mutate(
      {
        name: draft.name.trim(),
        headline: draft.headline.trim(),
        location: draft.location.trim(),
        email: draft.email.trim(),
        phone: draft.phone.trim(),
        summary: draft.summary.trim(),
        links: links
          .map(({ label, url }) => ({ label: label.trim(), url: url.trim() }))
          .filter(({ url }) => url)
          .map(({ label, url }) => ({
            label: label || URL.parse(url)?.hostname || url.slice(0, 40),
            url,
          })),
      },
      { onSuccess: onDone },
    );
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-5 pt-3">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(220px,100%),1fr))] gap-3.5">
        <TextField
          label={t("data.contact.name")}
          maxLength={200}
          autoFocus
          value={draft.name}
          onChange={(event) => set({ name: event.target.value })}
        />
        <TextField
          label={t("data.contact.headline")}
          placeholder={t("data.contact.headlinePlaceholder")}
          maxLength={200}
          value={draft.headline}
          onChange={(event) => set({ headline: event.target.value })}
        />
        <TextField
          label={t("data.contact.location")}
          maxLength={200}
          value={draft.location}
          onChange={(event) => set({ location: event.target.value })}
        />
        <TextField
          label={t("data.contact.email")}
          type="email"
          maxLength={320}
          value={draft.email}
          onChange={(event) => set({ email: event.target.value })}
        />
        <TextField
          label={t("data.contact.phone")}
          type="tel"
          maxLength={50}
          value={draft.phone}
          onChange={(event) => set({ phone: event.target.value })}
        />
      </div>
      <TextAreaField
        label={t("data.contact.summary")}
        rows={4}
        value={draft.summary}
        onChange={(event) => set({ summary: event.target.value })}
      />
      <fieldset className="m-0 flex flex-col gap-2.5 border-0 p-0">
        <legend className="text-ink-3 pb-1.5 text-sm">
          {t("data.contact.links")}
        </legend>
        {links.map((link, index) => (
          <div
            key={index}
            className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_40px] items-center gap-2.5"
          >
            <input
              aria-label={t("data.contact.linkLabel", { number: index + 1 })}
              placeholder={t("data.contact.linkLabelPlaceholder")}
              maxLength={40}
              value={link.label}
              onChange={(event) =>
                setLink(index, { label: event.target.value })
              }
              className="border-hair bg-ground text-ink min-h-10 min-w-0 rounded-lg border px-3 text-sm"
            />
            <input
              type="url"
              aria-label={t("data.contact.linkUrl", { number: index + 1 })}
              placeholder="https://"
              maxLength={500}
              value={link.url}
              onChange={(event) => setLink(index, { url: event.target.value })}
              className="border-hair bg-ground text-ink min-h-10 min-w-0 rounded-lg border px-3 text-sm"
            />
            <button
              type="button"
              aria-label={t("data.contact.removeLink", { number: index + 1 })}
              title={t("data.contact.remove")}
              onClick={() =>
                setLinks((current) => current.filter((_, at) => at !== index))
              }
              className="text-ink-3 hover:text-ink inline-flex size-10 cursor-pointer items-center justify-center rounded-lg"
            >
              <X size={16} />
            </button>
          </div>
        ))}
        <button
          type="button"
          disabled={links.length >= 3}
          onClick={() =>
            setLinks((current) => [...current, { label: "", url: "" }])
          }
          className="border-hair text-ink-2 inline-flex min-h-10 cursor-pointer items-center justify-center gap-1.5 rounded-lg border border-dashed text-sm font-semibold disabled:cursor-default disabled:opacity-45"
        >
          {t("data.contact.addLink")}
          <span className="text-ink-3 font-normal">
            {t("data.contact.linkLimit")}
          </span>
        </button>
      </fieldset>
      {update.isError && (
        <p role="alert" className="text-crit m-0 text-sm">
          {t("data.notSaved", { reason: update.error.message })}
        </p>
      )}
      <div className="flex justify-end gap-2.5">
        <button type="button" onClick={onDone} className={buttonClass()}>
          {t("data.cancel")}
        </button>
        <button
          type="submit"
          disabled={update.isPending}
          className={buttonClass("primary")}
        >
          {update.isPending ? t("data.saving") : t("data.save")}
        </button>
      </div>
    </form>
  );
}

export default function ContactCard({ profile }: { profile: Profile }) {
  const { t, i18n } = useTranslation();
  const [editing, setEditing] = useState(false);
  const { copied, copy } = useCopied();
  const rows: {
    key: string;
    label: string;
    text: string;
    href?: string;
    value?: string;
    long?: boolean;
  }[] = [
    { key: "name", label: t("data.contact.name"), text: profile.name },
    {
      key: "headline",
      label: t("data.contact.headline"),
      text: profile.headline,
    },
    {
      key: "location",
      label: t("data.contact.location"),
      text: profile.location,
    },
    {
      key: "email",
      label: t("data.contact.email"),
      text: profile.email,
      href: `mailto:${profile.email}`,
    },
    { key: "phone", label: t("data.contact.phone"), text: profile.phone },
    ...profile.links.map((link, index) => ({
      key: `link-${index}`,
      label: link.label,
      text: shortUrl(link.url),
      href: link.url,
      value: link.url,
    })),
    {
      key: "summary",
      label: t("data.contact.summary"),
      text: profile.summary,
      long: true,
    },
  ].filter((row) => row.text);
  const parts = [
    ...(["name", "email", "phone"] as const)
      .filter((key) => profile[key])
      .map((key) => t(`data.contact.parts.${key}`)),
    ...(profile.links.length
      ? [t("data.contact.parts.links", { count: profile.links.length })]
      : []),
  ];
  const listed = new Intl.ListFormat(i18n.language).format(parts);

  return (
    <Section
      title={t("data.contact.title")}
      hint={t("data.contact.hint")}
      summary={
        listed
          ? listed[0].toUpperCase() + listed.slice(1)
          : t("data.contact.empty")
      }
      defaultOpen
    >
      <div className="flex flex-col px-4 pb-5 sm:px-[22px]">
        {editing ? (
          <ContactForm profile={profile} onDone={() => setEditing(false)} />
        ) : (
          <>
            <div className="flex justify-end py-3">
              <button
                type="button"
                onClick={() => setEditing(true)}
                className={cn(buttonClass(), "min-h-9")}
              >
                <Pencil size={15} />
                {t("data.edit")}
              </button>
            </div>
            {rows.length === 0 ? (
              <p className="text-ink-3 m-0 text-sm">
                {t("data.contact.nothing")}
              </p>
            ) : (
              <dl className="m-0 flex flex-col">
                {rows.map((row) => (
                  <div
                    key={row.key}
                    className={cn(
                      "border-hair-soft grid min-h-12 grid-cols-[minmax(0,1fr)_36px] gap-x-3 border-t py-2 sm:grid-cols-[180px_minmax(0,1fr)_36px]",
                      row.long ? "items-start" : "items-center",
                    )}
                  >
                    <dt className="text-ink-3 col-span-2 text-sm sm:col-span-1 sm:pt-0">
                      {row.label}
                    </dt>
                    <dd
                      className={cn(
                        "m-0 min-w-0",
                        row.long
                          ? "whitespace-pre-line"
                          : "overflow-hidden text-ellipsis whitespace-nowrap",
                      )}
                    >
                      {row.href ? (
                        <a
                          href={row.href}
                          target={row.key === "email" ? undefined : "_blank"}
                          rel="noreferrer"
                          title={row.href}
                          className="text-ink decoration-hair underline underline-offset-4"
                        >
                          {row.text}
                        </a>
                      ) : (
                        row.text
                      )}
                    </dd>
                    <CopyIconButton
                      name={row.label}
                      copied={copied === row.key}
                      onCopy={() => copy(row.key, row.value ?? row.text)}
                    />
                  </div>
                ))}
              </dl>
            )}
          </>
        )}
      </div>
    </Section>
  );
}
