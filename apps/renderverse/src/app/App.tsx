import { RouterProvider, createBrowserRouter } from "react-router-dom";
import AppLayout from "./AppLayout";
import PortfolioMain from "./PortfolioMain";
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
