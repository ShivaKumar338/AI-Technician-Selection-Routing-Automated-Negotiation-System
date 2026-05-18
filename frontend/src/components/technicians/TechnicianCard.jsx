import { useState } from "react";
import { MapPin, Star, MessageCircle, Phone } from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "../../utils/cn";
import api from "../../api/axios";

export default function TechnicianCard({ technician, jobId }) {
  const skills = technician.skills || [];
  const [negotiating, setNegotiating] = useState(false);
  const [result, setResult] = useState(null);

  const handleWhatsAppNegotiate = async () => {
    if (!jobId) {
      toast.error("Create a job first, then negotiate from the job page");
      return;
    }
    setNegotiating(true);
    setResult(null);
    try {
      const { data } = await api.post(
        `/api/negotiate/${jobId}?tech_id=${technician.id}`
      );
      setResult(data);
      toast.success(`WhatsApp negotiation started with ${technician.name}`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setNegotiating(false);
    }
  };

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
          {technician.lat?.toFixed(3)}, {technician.lng?.toFixed(3)}
        </span>
        <span className="rounded-md bg-[#25D366]/10 px-2 py-0.5 text-xs font-medium text-[#25D366]">
          {technician.available ? "Ready to Negotiate" : "Unavailable"}
        </span>
      </div>

      {technician.phone_number && (
        <div className="mt-2 flex items-center gap-1 text-xs text-muted">
          <Phone className="h-3.5 w-3.5" />
          <span>{technician.phone_number}</span>
        </div>
      )}

      {/* WhatsApp Negotiate button */}
      <div className="mt-4 border-t border-border pt-4">
        <button
          type="button"
          onClick={handleWhatsAppNegotiate}
          disabled={negotiating || !technician.available}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition",
            "bg-[#25D366]/15 text-[#25D366] border border-[#25D366]/30",
            "hover:bg-[#25D366]/25 hover:border-[#25D366]/60",
            (negotiating || !technician.available) && "cursor-not-allowed opacity-50"
          )}
        >
          <MessageCircle className="h-4 w-4" />
          {negotiating ? "Opening WhatsApp..." : "Negotiate on WhatsApp"}
        </button>

        {result && (
          <div className="mt-2 rounded-lg bg-[#25D366]/10 border border-[#25D366]/20 p-2 text-xs">
            <p className="text-[#25D366] font-semibold">
              Negotiation initiated ✓
            </p>
            <p className="text-muted mt-0.5">
              Chatting with {result.phone_number}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
