import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  GraduationCap,
  Search,
  Zap,
} from "lucide-react";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/auto-teach", icon: Zap, label: "AutoTeach" },
  { to: "/documents", icon: FileText, label: "Documents" },
  { to: "/tutor", icon: GraduationCap, label: "AI Tutor" },
  { to: "/knowledge", icon: Search, label: "Knowledge" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-56 bg-zinc-900 border-r border-zinc-800 flex flex-col">
        <div className="p-4 border-b border-zinc-800">
          <h1 className="text-lg font-bold text-indigo-400 tracking-tight">
            LawFlow
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">Law School Study Engine</p>
        </div>
        <div className="flex-1 p-2 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-indigo-500/15 text-indigo-400"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto p-6">{children}</div>
      </main>
    </div>
  );
}
