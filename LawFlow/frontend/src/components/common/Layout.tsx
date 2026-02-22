import { useState } from "react";
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
  CircleHelp,
  Sun,
  Moon,
  Menu,
  X,
  User,
  Trophy,
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { useTutorial } from "@/context/TutorialContext";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/auto-teach", icon: Zap, label: "AutoTeach" },
  { to: "/exam", icon: FileQuestion, label: "Exam Sim" },
  { to: "/subjects", icon: BookOpen, label: "Subjects" },
  { to: "/tutor", icon: GraduationCap, label: "AI Tutor" },
  { to: "/flashcards", icon: CreditCard, label: "Flashcards" },
  { to: "/progress", icon: BarChart2, label: "Progress" },
  { to: "/rewards", icon: Trophy, label: "Rewards" },
  { to: "/documents", icon: FileText, label: "Documents" },
  { to: "/knowledge", icon: Search, label: "Knowledge" },
  { to: "/profile", icon: User, label: "Profile" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { theme, toggleTheme } = useTheme();
  const { openTutorial } = useTutorial();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const sidebar = (
    <>
      {/* Brand */}
      <div
        className="p-4 flex items-center justify-between"
        style={{ borderBottom: "1px solid var(--sidebar-border)" }}
      >
        <div>
          <h1 className="text-lg font-bold tracking-tight text-accent-label">
            LawFlow
          </h1>
          <p className="text-xs mt-0.5 text-ui-muted">
            Law School Study Engine
          </p>
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden p-1 rounded-lg hover:bg-white/10 text-ui-muted"
          aria-label="Close sidebar"
        >
          <X size={18} />
        </button>
      </div>

      {/* Nav links */}
      <div className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        <p className="text-[10px] font-semibold uppercase tracking-widest px-3 pt-3 pb-1 text-ui-muted">
          Navigation
        </p>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors relative ${
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
                {isActive && (
                  <span
                    className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full"
                    style={{ backgroundColor: "var(--accent)" }}
                  />
                )}
                <Icon size={16} />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>

      {/* Footer actions */}
      <div
        className="p-3 space-y-1"
        style={{ borderTop: "1px solid var(--sidebar-border)" }}
      >
        <button
          onClick={openTutorial}
          className="btn-ghost w-full justify-start text-sm"
          title="Show quick tutorial"
        >
          <CircleHelp size={16} />
          <span>Quick Tutorial</span>
        </button>
        <button
          onClick={toggleTheme}
          className="btn-ghost w-full justify-start text-sm"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
        </button>
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-base">
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay lg:hidden ${sidebarOpen ? "open" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar — always dark */}
      <nav
        className={`
          fixed inset-y-0 left-0 z-50 w-56 flex flex-col shrink-0
          transform transition-transform duration-200 ease-in-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        style={{
          backgroundColor: "var(--sidebar-bg)",
          borderRight: "1px solid var(--sidebar-border)",
        }}
      >
        {sidebar}
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-base">
        {/* Mobile top bar */}
        <div className="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-base border-b border-[var(--border)]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 rounded-lg hover:bg-[var(--bg-muted)] text-ui-primary"
            aria-label="Open sidebar"
          >
            <Menu size={20} />
          </button>
          <span className="text-sm font-bold text-accent-label">LawFlow</span>
        </div>

        <div className="max-w-6xl mx-auto p-4 sm:p-6 text-ui-primary animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
