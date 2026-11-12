import { Upload } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { useEntries, useProfile, useSkills } from "@/features/portfolio";
import { buttonClass } from "@/shared/components/button";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import { Tab, TabList, TabPanel, Tabs } from "@/shared/components/Tabs";
import ContactCard from "../components/ContactCard";
import EntryCard from "../components/EntryCard";
import ImportDialog from "../components/ImportDialog";
import NetworkingTab from "../components/NetworkingTab";
import PreferencesCard from "../components/PreferencesCard";
import SkillsCard from "../components/SkillsCard";
import { useChanges } from "../hooks/useData";
import { reviewCards } from "../lib/facts";

const INTRO_KEY = "ops:data-intro";

export default function DataPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const [importing, setImporting] = useState(false);
  const [intro, setIntro] = useState(
    () => localStorage.getItem(INTRO_KEY) !== "hidden",
  );
  const profile = useProfile();
  const entries = useEntries();
  const skills = useSkills();
  const changes = useChanges();
  const tab = params.get("tab") === "networking" ? "networking" : "about";
  const waiting = changes.data ? reviewCards(changes.data).length : 0;
  const failed = [profile, entries, skills].find((query) => query.isError);

  return (
    <>
      <PageHeader
        title={t("data.title")}
        subtitle={t("data.subtitle")}
        actions={
          <button
            type="button"
            onClick={() => setImporting(true)}
            className={buttonClass()}
          >
            <Upload size={15} className="text-ink-3" />
            {t("data.addFile")}
          </button>
        }
      />
      <PageBody>
        <div className="mx-auto flex w-full max-w-[760px] flex-col gap-5">
          {intro && (
            <section
              aria-labelledby="how-heading"
              className="bg-well flex flex-col gap-3.5 rounded-xl px-5 py-[18px]"
            >
              <div className="flex items-center justify-between gap-3">
                <h2 id="how-heading" className="m-0 text-[15px] font-semibold">
                  {t("data.how.title")}
                </h2>
                <button
                  type="button"
                  onClick={() => {
                    localStorage.setItem(INTRO_KEY, "hidden");
                    setIntro(false);
                  }}
                  className="text-amber min-h-9 cursor-pointer text-sm font-semibold"
                >
                  {t("data.how.dismiss")}
                </button>
              </div>
              <ol className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-4 p-0">
                {(["file", "check", "networking"] as const).map(
                  (step, index) => (
                    <li key={step} className="flex items-start gap-2.5">
                      <span
                        aria-hidden="true"
                        className="bg-panel border-hair text-amber flex size-6 flex-none items-center justify-center rounded-full border text-xs font-bold"
                      >
                        {index + 1}
                      </span>
                      <span className="flex flex-col gap-0.5">
                        <span className="text-sm font-semibold">
                          {t(`data.how.steps.${step}.title`)}
                        </span>
                        <span className="text-ink-2 text-[13px]">
                          {t(`data.how.steps.${step}.text`)}
                        </span>
                      </span>
                    </li>
                  ),
                )}
              </ol>
            </section>
          )}
          {waiting > 0 && (
            <Link
              to="/data/review"
              className="border-hair bg-warn-bg text-ink flex min-h-11 items-center gap-2.5 rounded-[10px] border px-4 py-2.5 text-sm no-underline"
            >
              <span
                aria-hidden="true"
                className="bg-amber size-2 flex-none rounded-full"
              />
              <span className="flex-1">
                {t("data.pending", { count: waiting })}
              </span>
              <span className="text-amber font-semibold">
                {t("data.choose")}
              </span>
            </Link>
          )}
          {failed?.error ? (
            <StateMessage tone="error">
              {t("data.loadFailed", { reason: failed.error.message })}
            </StateMessage>
          ) : !profile.data || !entries.data || !skills.data ? (
            <StateMessage>{t("common.loading")}</StateMessage>
          ) : (
            <Tabs
              value={tab}
              onValueChange={(next) =>
                setParams(next === "about" ? {} : { tab: next })
              }
              className="flex flex-col gap-5"
            >
              <TabList aria-label={t("data.tabs.label")}>
                <Tab value="about">{t("data.tabs.about")}</Tab>
                <Tab value="networking">{t("data.tabs.networking")}</Tab>
              </TabList>
              <TabPanel value="about" className="flex flex-col gap-5">
                <ContactCard profile={profile.data} />
                <PreferencesCard preferences={profile.data.preferences} />
                {(["role", "education", "project"] as const).map((kind) => (
                  <EntryCard
                    key={kind}
                    kind={kind}
                    entries={entries.data.filter(
                      (entry) => entry.kind === kind,
                    )}
                  />
                ))}
                <SkillsCard skills={skills.data} />
              </TabPanel>
              <TabPanel value="networking">
                <NetworkingTab entries={entries.data} skills={skills.data} />
              </TabPanel>
            </Tabs>
          )}
        </div>
      </PageBody>
      <ImportDialog open={importing} onClose={() => setImporting(false)} />
    </>
  );
}
