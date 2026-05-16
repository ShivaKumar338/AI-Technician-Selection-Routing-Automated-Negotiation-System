import { Outlet } from "react-router-dom";
import { useLiveJobsCount } from "../../hooks/useLiveJobsCount";
import Sidebar from "./Sidebar";

export default function LayoutShell() {
  const { count } = useLiveJobsCount(10000);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar liveJobsCount={count} />
      <main className="flex-1 overflow-y-auto p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}
