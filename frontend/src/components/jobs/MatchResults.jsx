import { Star, MapPin, BadgeCheck } from "lucide-react";
import { formatScore } from "../../utils/format";

export default function MatchResults({ matches, onNegotiate, negotiatingId }) {
  if (!matches?.length) {
    return (
      <p className="text-sm text-muted">Submit a job to see ranked matches here.</p>
    );
  }

  return (
    <div className="space-y-4">
      {matches.map((tech, index) => (
        <div
          key={tech.id}
          className="rounded-xl border border-border bg-background/60 p-4 transition hover:border-primary/40"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 text-xs font-bold text-primary">
                  #{index + 1}
                </span>
                <h3 className="font-semibold text-foreground">{tech.name}</h3>
                {tech.available && <BadgeCheck className="h-4 w-4 text-primary" />}
              </div>
              <p className="mt-1 text-sm text-muted capitalize">
                {(tech.skills || []).join(" · ")}
              </p>
            </div>
            <button
              type="button"
              className="btn-primary text-xs"
              disabled={negotiatingId === tech.id}
              onClick={() => onNegotiate(tech)}
            >
              {negotiatingId === tech.id ? "Negotiating..." : "Start Negotiation"}
            </button>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-muted">Score</p>
              <p className="font-semibold text-primary">{formatScore(tech.score)}</p>
            </div>
            <div>
              <p className="text-muted">Distance</p>
              <p className="font-semibold">{tech.distance_km} km</p>
            </div>
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4 text-amber-400" />
              <span>{tech.rating}/5</span>
            </div>
            <div className="flex items-center gap-1">
              <MapPin className="h-4 w-4 text-muted" />
              <span>From ₹{tech.rate_min}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
