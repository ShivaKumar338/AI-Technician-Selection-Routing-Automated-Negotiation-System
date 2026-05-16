import { NavLink } from "react-router-dom";
import { Activity, Bot, LayoutDashboard, Plus, Users } from "lucide-react";
import { cn } from "../../utils/cn";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/jobs/new", label: "New Job", icon: Plus },
  { to: "/technicians", label: "Technicians", icon: Users },
];

export default function Sidebar({ liveJobsCount = 0 }) {
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-card px-4 py-6">
      <div className="mb-8 flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15">
          <Bot className="h-6 w-6 text-primary" />
        </div>
        <div>
          <p className="text-lg font-bold text-primary">TechRoute</p>
          <p className="text-xs font-semibold tracking-wide text-primary/80">AI</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-2">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn("nav-link", isActive && "nav-link-active")
            }
          >
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="card-surface mt-4 p-4">
        <div className="mb-2 flex items-center gap-2 text-muted">
          <Activity className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">Live Jobs</span>
        </div>
        <p className="text-3xl font-bold text-foreground">{liveJobsCount}</p>
      </div>
    </aside>
  );
}
