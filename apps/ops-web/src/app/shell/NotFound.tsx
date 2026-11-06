import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import PageBody from "@/shared/ui/PageBody";
import PageHeader from "@/shared/ui/PageHeader";
import StateMessage from "@/shared/ui/StateMessage";

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
