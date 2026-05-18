import { getStatusStyle, getStatusLabel } from "../../utils/jobStatus";
import { cn } from "../../utils/cn";

export default function StatusBadge({ status }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold",
        getStatusStyle(status)
      )}
    >
      {getStatusLabel(status)}
    </span>
  );
}
