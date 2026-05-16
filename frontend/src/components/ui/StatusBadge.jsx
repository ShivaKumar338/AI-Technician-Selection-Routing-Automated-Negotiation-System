import { getStatusStyle } from "../../utils/jobStatus";
import { cn } from "../../utils/cn";

export default function StatusBadge({ status }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold capitalize",
        getStatusStyle(status)
      )}
    >
      {status}
    </span>
  );
}
