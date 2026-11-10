import { Sparkle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import { Tab, TabList, TabPanel, Tabs } from "@/shared/components/Tabs";
import { cn } from "@/shared/lib/cn";
import AboutPanel from "../components/AboutPanel";
import ChangesTab from "../components/ChangesTab";
import EntrySection from "../components/EntrySection";
import PreferencesPanel from "../components/PreferencesPanel";
import ProjectsTab from "../components/ProjectsTab";
import ReleasesAside from "../components/ReleasesAside";
import SkillsTab from "../components/SkillsTab";
import { useDraft, usePublish, useReleases } from "../hooks/usePortfolio";
import {
  useEntries,
  useProfile,
  useSkills,
  useUpdateProfile,
} from "../hooks/useProfile";

const TABS = ["profile", "skills", "projects", "releases"] as const;
type PortfolioTab = (typeof TABS)[number];

export default function PortfolioPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const profile = useProfile();
  const entries = useEntries();
  const skills = useSkills();
  const update = useUpdateProfile();
  const draft = useDraft();
  const releases = useReleases();
  const publish = usePublish();
  const site = draft.data?.site_url ?? null;
  const tabs = site ? TABS : TABS.filter((name) => name !== "releases");
  const tab: PortfolioTab =
    tabs.find((name) => name === params.get("tab")) ?? "projects";

  const saveStatus = update.isPending
    ? t("portfolio.save.saving")
    : update.isError
      ? t("portfolio.save.failed", { reason: update.error.message })
      : update.isSuccess
        ? t("portfolio.save.saved")
        : null;
  const failed = [profile, entries, skills, draft, releases].find(
    (query) => query.isError,
  );

  return (
    <>
      <PageHeader
        title={t("portfolio.title")}
        subtitle={t("portfolio.subtitle")}
        actions={
          !draft.data ? null : site ? (
            <>
              <a
                href={site}
                target="_blank"
                rel="noreferrer"
                className={cn(buttonClass(), "min-h-[42px]")}
              >
                {t("portfolio.previewSite")}
              </a>
              <button
                type="button"
                className={buttonClass("primary")}
                disabled={draft.data.changes.length === 0 || publish.isPending}
                onClick={() => publish.mutate()}
              >
                <Sparkle size={14} className="text-amber-soft" />
                {t("portfolio.publish", { number: draft.data.number })}
              </button>
            </>
          ) : (
            <button
              type="button"
              className={buttonClass("primary")}
              onClick={() =>
                setParams({ tab: "projects", edit: "new-project" })
              }
            >
              <Sparkle size={14} className="text-amber-soft" />
              {t("portfolio.addProject")}
            </button>
          )
        }
      />
      <PageBody>
        {failed?.error ? (
          <StateMessage tone="error">
            {t("portfolio.loadFailed", { reason: failed.error.message })}
          </StateMessage>
        ) : !profile.data ||
          !entries.data ||
          !skills.data ||
          !draft.data ||
          !releases.data ? (
          <StateMessage>{t("common.loading")}</StateMessage>
        ) : (
          <Tabs
            value={tab}
            onValueChange={(next) => setParams({ tab: next })}
            className="flex flex-col gap-7"
          >
            <TabList aria-label={t("portfolio.tabs.label")}>
              {tabs.map((name) => (
                <Tab key={name} value={name}>
                  {t(`portfolio.tabs.${name}`)}
                </Tab>
              ))}
            </TabList>
            <TabPanel value="profile" className="flex flex-col gap-7">
              {saveStatus && (
                <span
                  role="status"
                  className={
                    update.isError ? "text-crit text-sm" : "text-ink-3 text-sm"
                  }
                >
                  {saveStatus}
                </span>
              )}
              <div className="grid grid-cols-[repeat(auto-fit,minmax(min(420px,100%),1fr))] items-start gap-6">
                <AboutPanel profile={profile.data} onChange={update.mutate} />
                <PreferencesPanel
                  preferences={profile.data.preferences}
                  onChange={update.mutate}
                />
              </div>
              <EntrySection
                kind="role"
                entries={entries.data.filter((e) => e.kind === "role")}
              />
              <EntrySection
                kind="education"
                entries={entries.data.filter((e) => e.kind === "education")}
              />
            </TabPanel>
            <TabPanel value="skills">
              <SkillsTab skills={skills.data} />
            </TabPanel>
            <TabPanel
              value="projects"
              className="flex flex-wrap items-start gap-6"
            >
              <div className="flex min-w-0 flex-[999_1_560px] flex-col">
                <ProjectsTab entries={entries.data} />
              </div>
              {site && (
                <ReleasesAside
                  draft={draft.data}
                  releases={releases.data}
                  publishError={publish.isError ? publish.error.message : null}
                  limit={3}
                />
              )}
            </TabPanel>
            {site && (
              <TabPanel
                value="releases"
                className="flex flex-wrap items-start gap-6"
              >
                <ChangesTab draft={draft.data} />
                <ReleasesAside
                  draft={draft.data}
                  releases={releases.data}
                  publishError={publish.isError ? publish.error.message : null}
                />
              </TabPanel>
            )}
          </Tabs>
        )}
      </PageBody>
    </>
  );
}
