import { MapPin, Star } from "lucide-react";
import { cn } from "../../utils/cn";

export default function TechnicianCard({ technician }) {
  const skills = technician.skills || [];

  return (
    <div
      className={cn(
        "card-surface p-5 transition hover:border-primary/30",
        !technician.available && "opacity-70"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-foreground">{technician.name}</h3>
          <div className="mt-1 flex items-center gap-1 text-sm text-amber-400">
            <Star className="h-4 w-4 fill-amber-400" />
            <span>{technician.rating}</span>
          </div>
        </div>
        <span
          className={cn(
            "rounded-lg px-2 py-1 text-xs font-semibold",
            technician.available
              ? "bg-primary/20 text-primary"
              : "bg-slate-500/20 text-slate-300"
          )}
        >
          {technician.available ? "Available" : "Busy"}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {skills.map((skill) => (
          <span
            key={skill}
            className="rounded-lg bg-background px-2 py-1 text-xs capitalize text-muted"
          >
            {skill}
          </span>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between text-sm text-muted">
        <span className="flex items-center gap-1">
          <MapPin className="h-4 w-4" />
          {technician.lat?.toFixed(4)}, {technician.lng?.toFixed(4)}
        </span>
        <span className="font-medium text-foreground">From ₹{technician.rate_min}</span>
      </div>
    </div>
  );
}
