import { useMemo } from "react";
import { fetchJobs } from "../api/jobs";
import { usePolling } from "./usePolling";

export function useLiveJobsCount(intervalMs = 10000) {
  const { data: jobs, loading } = usePolling(fetchJobs, intervalMs);

  const count = useMemo(() => {
    if (!jobs) return 0;
    return jobs.filter((job) => job.status !== "completed").length;
  }, [jobs]);

  return { count, loading };
}
