import { RouterProvider, createBrowserRouter } from "react-router-dom";
import AppLayout from "./ui/AppLayout";
import PortfolioMain from "./ui/PortfolioMain";
import { useEffect } from "react";

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        path: "/",
        element: <PortfolioMain />,
      },
    ],
  },
]);

function App() {
  useEffect(() => {
    const sessionId = sessionStorage.getItem("sessionId");
    if (!sessionId) {
      sessionStorage.setItem("sessionId", crypto.randomUUID());
    }
  }, []);

  return <RouterProvider router={router} />;
}

export default App;
