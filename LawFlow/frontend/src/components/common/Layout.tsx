import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  GraduationCap,
  Search,
  Zap,
  BookOpen,
  CreditCard,
  BarChart2,
  FileQuestion,
  Sun,
  Moon,
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/auto-teach", icon: Zap, label: "AutoTeach" },
  { to: "/exam", icon: FileQuestion, label: "Exam Sim" },
  { to: "/subjects", icon: BookOpen, label: "Subjects" },
  { to: "/tutor", icon: GraduationCap, label: "AI Tutor" },
  { to: "/flashcards", icon: CreditCard, label: "Flashcards" },
  { to: "/progress", icon: BarChart2, label: "Progress" },
  { to: "/documents", icon: FileText, label: "Documents" },
  { to: "/knowledge", icon: Search, label: "Knowledge" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex h-screen" style={{ backgroundColor: "var(--bg-base)" }}>
      {/* Sidebar — always dark */}
      <nav
        className="w-56 flex flex-col shrink-0"
        style={{
          backgroundColor: "var(--sidebar-bg)",
          borderRight: "1px solid var(--sidebar-border)",
        }}
      >
        {/* Brand */}
        <div
          className="p-4"
          style={{ borderBottom: "1px solid var(--sidebar-border)" }}
        >
          <h1 className="text-lg font-bold tracking-tight" style={{ color: "var(--accent-text)" }}>
            LawFlow
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Law School Study Engine
          </p>
        </div>

        {/* Nav links */}
        <div className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          <p
            className="text-[10px] font-semibold uppercase tracking-widest px-3 pt-3 pb-1"
            style={{ color: "var(--text-muted)" }}
          >
            Navigation
          </p>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? "sidebar-active" : "sidebar-inactive"
                }`
              }
              style={({ isActive }) => ({
                backgroundColor: isActive ? "var(--sidebar-active-bg)" : "transparent",
                color: isActive ? "var(--sidebar-active-text)" : "var(--text-muted)",
              })}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    size={16}
                    style={{ color: isActive ? "var(--sidebar-active-text)" : "var(--text-muted)" }}
                  />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>

        {/* Theme toggle */}
        <div
          className="p-3"
          style={{ borderTop: "1px solid var(--sidebar-border)" }}
        >
          <button
            onClick={toggleTheme}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-white/10"
            style={{ color: "var(--text-muted)" }}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main
        className="flex-1 overflow-auto"
        style={{ backgroundColor: "var(--bg-base)" }}
      >
        <div className="max-w-6xl mx-auto p-6" style={{ color: "var(--text-primary)" }}>
          {children}
        </div>
      </main>
    </div>
  );
}
