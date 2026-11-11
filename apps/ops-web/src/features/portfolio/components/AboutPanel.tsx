import { useTranslation } from "react-i18next";
import DraftTextField from "@/shared/components/DraftTextField";
import Panel from "@/shared/components/Panel";
import type { Profile, ProfilePatch } from "../api/profile";

interface AboutPanelProps {
  profile: Profile;
  onChange: (patch: ProfilePatch) => void;
}

export default function AboutPanel({ profile, onChange }: AboutPanelProps) {
  const { t } = useTranslation();

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
      <DraftTextField
        label={t("portfolio.about.links")}
        multiline
        value={profile.links.join("\n")}
        onSave={(links) =>
          onChange({
            links: links
              .split("\n")
              .map((link) => link.trim())
              .filter(Boolean),
          })
        }
      />
      <DraftTextField
        label={t("portfolio.about.summary")}
        multiline
        value={profile.summary}
        onSave={(summary) => onChange({ summary })}
      />
    </Panel>
  );
}
