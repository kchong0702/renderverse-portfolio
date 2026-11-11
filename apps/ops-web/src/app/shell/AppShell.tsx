import { useTranslation } from "react-i18next";
import { Outlet, useLocation } from "react-router-dom";
import { AssistantDock } from "@/features/assistant";
import { navItemAt } from "./nav";
import Sidebar from "./Sidebar";

export default function AppShell() {
  const { t } = useTranslation();
  const item = navItemAt(useLocation().pathname);

  return (
    <div className="flex min-h-screen flex-wrap min-[792px]:h-screen min-[792px]:flex-nowrap">
      <Sidebar />
      <main className="flex min-w-0 flex-[999_1_560px] flex-col">
        <Outlet />
      </main>
      <AssistantDock
        topic={item && t(`nav.items.${item.key}`)}
        suggestions={
          item
            ? t(`assistant.suggestions.${item.key}`, { returnObjects: true })
            : []
        }
      />
    </div>
  );
}
