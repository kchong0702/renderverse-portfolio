import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function AppShell() {
  return (
    <div className="flex min-h-screen flex-wrap">
      <Sidebar />
      <main className="flex min-w-0 flex-[999_1_560px] flex-col">
        <Outlet />
      </main>
    </div>
  );
}
