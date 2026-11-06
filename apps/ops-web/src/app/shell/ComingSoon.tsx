import { useTranslation } from "react-i18next";
import PageBody from "@/shared/ui/PageBody";
import PageHeader from "@/shared/ui/PageHeader";
import StateMessage from "@/shared/ui/StateMessage";
import type { NavKey } from "./nav";

/** Stands in for a screen whose feature has not been built yet */
export default function ComingSoon({ page }: { page: NavKey }) {
  const { t } = useTranslation();
  return (
    <>
      <PageHeader title={t(`nav.items.${page}`)} />
      <PageBody>
        <StateMessage>{t("shell.comingSoon")}</StateMessage>
      </PageBody>
    </>
  );
}
