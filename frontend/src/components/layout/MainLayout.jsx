import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function MainLayout({ liveJobsCount = 0 }) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar liveJobsCount={liveJobsCount} />
      <main className="flex-1 overflow-y-auto p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}
