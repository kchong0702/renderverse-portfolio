import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import DraftTextField from "@/shared/components/DraftTextField";
import { TextField } from "@/shared/components/fields";
import Panel from "@/shared/components/Panel";
import type { Profile, ProfileLink, ProfilePatch } from "../api/profile";

const slotsOf = (links: ProfileLink[]) =>
  Array.from(
    { length: 3 },
    (_, index) => links[index] ?? { label: "", url: "" },
  );

interface AboutPanelProps {
  profile: Profile;
  onChange: (patch: ProfilePatch) => void;
}

export default function AboutPanel({ profile, onChange }: AboutPanelProps) {
  const { t } = useTranslation();
  const [slots, setSlots] = useState(() => slotsOf(profile.links));

  useEffect(() => setSlots(slotsOf(profile.links)), [profile.links]);

  const setSlot = (index: number, change: Partial<ProfileLink>) =>
    setSlots((current) =>
      current.map((slot, at) => (at === index ? { ...slot, ...change } : slot)),
    );
  const saveLinks = () => {
    const links = slots
      .map(({ label, url }) => ({ label: label.trim(), url: url.trim() }))
      .filter(({ url }) => url)
      .map(({ label, url }) => ({
        label: label || URL.parse(url)?.hostname || url.slice(0, 40),
        url,
      }));
    if (JSON.stringify(links) !== JSON.stringify(profile.links)) {
      onChange({ links });
    }
  };

  return (
    <Panel title={t("portfolio.about.title")}>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(220px,100%),1fr))] gap-3.5">
        <DraftTextField
          label={t("portfolio.about.name")}
          maxLength={200}
          value={profile.name}
          onSave={(name) => onChange({ name })}
        />
        <DraftTextField
          label={t("portfolio.about.headline")}
          placeholder={t("portfolio.about.headlinePlaceholder")}
          maxLength={200}
          value={profile.headline}
          onSave={(headline) => onChange({ headline })}
        />
        <DraftTextField
          label={t("portfolio.about.location")}
          maxLength={200}
          value={profile.location}
          onSave={(location) => onChange({ location })}
        />
        <DraftTextField
          label={t("portfolio.about.email")}
          type="email"
          maxLength={320}
          value={profile.email}
          onSave={(email) => onChange({ email })}
        />
        <DraftTextField
          label={t("portfolio.about.phone")}
          type="tel"
          maxLength={50}
          value={profile.phone}
          onSave={(phone) => onChange({ phone })}
        />
      </div>
      <fieldset
        className="m-0 flex flex-col gap-2.5 border-0 p-0"
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) saveLinks();
        }}
      >
        <legend className="text-ink-3 pb-1.5 text-sm">
          {t("portfolio.about.links")}
        </legend>
        {slots.map((slot, index) => (
          <div
            key={index}
            className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-2.5"
          >
            <TextField
              label={t("portfolio.about.linkLabel", { number: index + 1 })}
              placeholder={t("portfolio.about.linkLabelPlaceholder")}
              maxLength={40}
              value={slot.label}
              onChange={(event) =>
                setSlot(index, { label: event.target.value })
              }
            />
            <TextField
              label={t("portfolio.about.linkUrl", { number: index + 1 })}
              type="url"
              placeholder="https://"
              maxLength={500}
              value={slot.url}
              onChange={(event) => setSlot(index, { url: event.target.value })}
            />
          </div>
        ))}
      </fieldset>
      <DraftTextField
        label={t("portfolio.about.summary")}
        multiline
        value={profile.summary}
        onSave={(summary) => onChange({ summary })}
      />
    </Panel>
  );
}
