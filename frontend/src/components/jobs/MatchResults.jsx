import { Star, BadgeCheck, MessageCircle } from "lucide-react";
import { formatScore } from "../../utils/format";

export default function MatchResults({ matches, onWhatsApp, whatsappId }) {
  if (!matches?.length) {
    return <p className="text-sm text-muted">Submit a job to see ranked matches here.</p>;
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
              className="flex items-center gap-1.5 rounded-lg border border-[#25D366]/30 bg-[#25D366]/10 px-3 py-1.5 text-xs font-semibold text-[#25D366] hover:bg-[#25D366]/20 transition disabled:opacity-50"
              disabled={whatsappId === tech.id}
              onClick={() => onWhatsApp(tech)}
            >
              <MessageCircle className="h-3.5 w-3.5" />
              {whatsappId === tech.id ? "Starting..." : "Negotiate on WhatsApp"}
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
            <div>
              <span className="rounded-md bg-[#25D366]/10 px-2 py-0.5 text-xs font-medium text-[#25D366]">
                Ready to Negotiate
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
