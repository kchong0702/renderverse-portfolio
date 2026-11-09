import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import PageBody from "@/shared/components/PageBody";
import PageHeader from "@/shared/components/PageHeader";
import StateMessage from "@/shared/components/StateMessage";

export default function NotFound() {
  const { t } = useTranslation();
  return (
    <>
      <PageHeader title={t("shell.notFound.title")} />
      <PageBody>
        <StateMessage>
          {t("shell.notFound.body")}{" "}
          <Link to="/" className="text-ink font-semibold underline">
            {t("shell.notFound.home")}
          </Link>
        </StateMessage>
      </PageBody>
    </>
  );
}
