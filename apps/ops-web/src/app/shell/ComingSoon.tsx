import { useTranslation } from "react-i18next";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";
import type { NavKey } from "./nav";

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
