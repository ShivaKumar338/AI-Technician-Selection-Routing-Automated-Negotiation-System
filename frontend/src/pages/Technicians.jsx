import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Users } from "lucide-react";
import { fetchTechnicians, seedTechnicians } from "../api/technicians";
import TechnicianCard from "../components/technicians/TechnicianCard";
import TechnicianFilters from "../components/technicians/TechnicianFilters";
import PageHeader from "../components/ui/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import { Skeleton } from "../components/ui/Skeleton";
import { usePolling } from "../hooks/usePolling";

export default function Technicians() {
  const [search, setSearch] = useState("");
  const [skill, setSkill] = useState("");
  const [availableOnly, setAvailableOnly] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const load = useCallback(() => fetchTechnicians(), []);
  const { data: technicians, loading, error, refresh } = usePolling(load, 15000);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);

  const filtered = useMemo(() => {
    const list = technicians || [];
    return list.filter((tech) => {
      if (availableOnly && !tech.available) return false;
      if (skill && !(tech.skills || []).some((s) => s.toLowerCase() === skill.toLowerCase())) {
        return false;
      }
      if (!search.trim()) return true;
      const query = search.toLowerCase();
      const inName = tech.name?.toLowerCase().includes(query);
      const inSkills = (tech.skills || []).some((s) => s.toLowerCase().includes(query));
      return inName || inSkills;
    });
  }, [technicians, search, skill, availableOnly]);

  const total = technicians?.length || 0;
  const availableCount = (technicians || []).filter((t) => t.available).length;

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const result = await seedTechnicians();
      toast.success(result.message || "Technicians seeded");
      refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Technicians"
        subtitle={`${total} total · ${availableCount} available`}
        action={
          <button type="button" className="btn-primary" onClick={handleSeed} disabled={seeding}>
            {seeding ? "Seeding..." : "Seed Demo Data"}
          </button>
        }
      />
      <TechnicianFilters
        search={search}
        onSearchChange={setSearch}
        skill={skill}
        onSkillChange={setSkill}
        availableOnly={availableOnly}
        onAvailableOnlyChange={setAvailableOnly}
      />
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <Skeleton key={n} className="h-44 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card-surface">
          <EmptyState
            icon={Users}
            title="No technicians match your filters"
            description="Try clearing filters or seed demo technicians."
            action={
              <button type="button" className="text-primary hover:underline" onClick={() => {
                setSearch("");
                setSkill("");
                setAvailableOnly(false);
              }}>
                Clear filters
              </button>
            }
          />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((tech) => (
            <TechnicianCard key={tech.id} technician={tech} />
          ))}
        </div>
      )}
    </div>
  );
}
