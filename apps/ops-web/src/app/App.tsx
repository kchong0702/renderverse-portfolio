import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { ApplicationsPage } from "@/features/applications";
import { RequireAuth, SignInPage, useIsAdmin } from "@/features/auth";
import { CalendarPage } from "@/features/calendar";
import { DashboardPage } from "@/features/dashboard";
import { DocumentsPage, ImportPage } from "@/features/documents";
import { InboxPage } from "@/features/inbox";
import { JobsPage } from "@/features/jobs";
import { PortfolioPage } from "@/features/portfolio";
import { SettingsPage } from "@/features/settings";
import { useApplyTheme } from "@/shared/theme/useApplyTheme";
import AppShell from "./shell/AppShell";
import NotFound from "./shell/NotFound";

function PortfolioRoute() {
  return useIsAdmin() ? <PortfolioPage /> : <NotFound />;
}

const router = createBrowserRouter(
  [
    { path: "/sign-in", element: <SignInPage /> },
    {
      element: (
        <RequireAuth>
          <AppShell />
        </RequireAuth>
      ),
      children: [
        { path: "/", element: <DashboardPage /> },
        { path: "/jobs", element: <JobsPage /> },
        { path: "/applications", element: <ApplicationsPage /> },
        { path: "/documents", element: <DocumentsPage /> },
        { path: "/documents/import", element: <ImportPage /> },
        { path: "/portfolio", element: <PortfolioRoute /> },
        { path: "/inbox", element: <InboxPage /> },
        { path: "/calendar", element: <CalendarPage /> },
        { path: "/settings", element: <SettingsPage /> },
        { path: "*", element: <NotFound /> },
      ],
    },
  ],
  {
    future: {
      v7_fetcherPersist: true,
      v7_normalizeFormMethod: true,
      v7_partialHydration: true,
      v7_relativeSplatPath: true,
      v7_skipActionErrorRevalidation: true,
    },
  },
);

function App() {
  useApplyTheme();

  return (
    <RouterProvider router={router} future={{ v7_startTransition: true }} />
  );
}

export default App;
