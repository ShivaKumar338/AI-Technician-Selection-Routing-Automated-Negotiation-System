import { useCallback, useEffect } from "react";
import toast from "react-hot-toast";
import { fetchJobs } from "../api/jobs";
import { fetchStats } from "../api/stats";
import { fetchTechnicians } from "../api/technicians";
import StatsCards from "../components/dashboard/StatsCards";
import TechnicianMap from "../components/dashboard/TechnicianMap";
import RecentJobs from "../components/dashboard/RecentJobs";
import PageHeader from "../components/ui/PageHeader";
import { usePolling } from "../hooks/usePolling";

export default function Dashboard() {
  const loadStats = useCallback(() => fetchStats(), []);
  const loadJobs = useCallback(() => fetchJobs(), []);
  const loadTechnicians = useCallback(() => fetchTechnicians(), []);

  const {
    data: stats,
    loading: statsLoading,
    error: statsError,
  } = usePolling(loadStats, 15000);
  const {
    data: jobs,
    loading: jobsLoading,
    error: jobsError,
  } = usePolling(loadJobs, 15000);
  const {
    data: technicians,
    loading: techLoading,
    error: techError,
  } = usePolling(loadTechnicians, 20000);

  useEffect(() => {
    if (statsError) toast.error(statsError);
  }, [statsError]);
  useEffect(() => {
    if (jobsError) toast.error(jobsError);
  }, [jobsError]);
  useEffect(() => {
    if (techError) toast.error(techError);
  }, [techError]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Real-time overview of jobs, technicians, and AI negotiations"
      />
      <StatsCards stats={stats} loading={statsLoading} />
      <TechnicianMap technicians={technicians} loading={techLoading} />
      <RecentJobs jobs={jobs} loading={jobsLoading} />
    </div>
  );
}
