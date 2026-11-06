import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { RequireAuth, SignInPage } from "@/features/auth";
import { useApplyTheme } from "@/shared/theme/useApplyTheme";
import AppShell from "./shell/AppShell";
import ComingSoon from "./shell/ComingSoon";
import NotFound from "./shell/NotFound";

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
        { path: "/", element: <ComingSoon page="dashboard" /> },
        { path: "/jobs", element: <ComingSoon page="jobs" /> },
        { path: "/applications", element: <ComingSoon page="applications" /> },
        { path: "/documents", element: <ComingSoon page="documents" /> },
        { path: "/portfolio", element: <ComingSoon page="portfolio" /> },
        { path: "/inbox", element: <ComingSoon page="inbox" /> },
        { path: "/calendar", element: <ComingSoon page="calendar" /> },
        { path: "/settings", element: <ComingSoon page="settings" /> },
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
