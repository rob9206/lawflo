import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  FileText,
  MessageSquare,
  Zap,
  BookOpen,
  ClipboardCheck,
  BarChart3,
  Brain,
  User,
  Trophy,
  CircleHelp,
  Menu,
  X,
  LayoutDashboard,
  CreditCard,
  Crown,
  LogOut,
  Search,
  Sun,
  Moon,
} from "lucide-react";
import { useTutorial } from "@/context/TutorialContext";
import { useTheme } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/documents", icon: FileText, label: "Documents" },
  { to: "/tutor", icon: MessageSquare, label: "Tutor" },
  { to: "/auto-teach", icon: Zap, label: "AutoTeach", proHint: true },
  { to: "/flashcards", icon: CreditCard, label: "Flashcards" },
  { to: "/exam", icon: ClipboardCheck, label: "Exam" },
  { to: "/subjects", icon: BookOpen, label: "Subjects" },
  { to: "/progress", icon: BarChart3, label: "Progress" },
  { to: "/knowledge", icon: Search, label: "Knowledge" },
  { to: "/rewards", icon: Trophy, label: "Rewards" },
  { to: "/pricing", icon: Crown, label: "Pricing" },
  { to: "/profile", icon: User, label: "Profile" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { openTutorial } = useTutorial();
  const { theme, toggleTheme } = useTheme();
  const { user, isPro, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const sidebar = (
    <>
      <div
        className="p-4 flex items-center justify-between"
        style={{ borderBottom: "2px solid var(--border)" }}
      >
        <div>
          <h1
            className="text-lg tracking-tight"
            style={{ fontWeight: 900, color: "var(--navy)" }}
          >
            LawFlow
          </h1>
          <p
            className="text-xs mt-0.5"
            style={{ color: "var(--text-muted)", fontWeight: 600 }}
          >
            Law School Study Engine
          </p>
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden p-1 rounded-lg"
          style={{ color: "var(--text-muted)" }}
          aria-label="Close sidebar"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        <p
          className="px-3 pt-3 pb-1"
          style={{
            fontSize: "11px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--text-muted)",
          }}
        >
          Navigation
        </p>
        {navItems.map(({ to, icon: Icon, label, proHint }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setSidebarOpen(false)}
            className="flex items-center gap-3 px-3 py-2.5 transition-colors"
            style={({ isActive }) => ({
              backgroundColor: isActive ? "var(--blue-bg)" : "transparent",
              color: isActive ? "var(--blue-dark)" : "var(--text-secondary)",
              borderRadius: "var(--radius-md)",
              fontSize: "15px",
              fontWeight: isActive ? 800 : 700,
            })}
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={20}
                  style={{ color: isActive ? "var(--blue)" : undefined }}
                />
                <span>{label}</span>
                {proHint && !isPro && (
                  <span className="duo-badge duo-badge-gold" style={{ marginLeft: "auto" }}>
                    PRO
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </div>

      <div
        className="p-3 space-y-1"
        style={{ borderTop: "2px solid var(--border)" }}
      >
        <div
          className="p-3 mb-2"
          style={{
            borderRadius: "var(--radius-md)",
            border: "2px solid var(--border)",
            background: "var(--surface-bg)",
          }}
        >
          <div className="flex items-center justify-between">
            <p style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>
              {user?.display_name || "Law Student"}
            </p>
            <span className={isPro ? "duo-badge duo-badge-gold" : "duo-badge duo-badge-blue"}>
              {isPro ? "PRO" : "FREE"}
            </span>
          </div>
          <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)" }}>
            {user?.email || ""}
          </p>
        </div>
        {!isPro && (
          <button
            onClick={() => navigate("/pricing")}
            className="duo-btn duo-btn-green w-full justify-start text-sm"
            style={{ textTransform: "none", fontWeight: 700, letterSpacing: "normal", padding: "8px 12px" }}
          >
            <Crown size={16} />
            <span>Upgrade to Pro</span>
          </button>
        )}
        <button
          onClick={openTutorial}
          className="duo-btn duo-btn-ghost w-full justify-start text-sm"
          style={{ textTransform: "none", fontWeight: 700, letterSpacing: "normal", padding: "8px 12px" }}
        >
          <CircleHelp size={16} />
          <span>Quick Tutorial</span>
        </button>
        <button
          onClick={toggleTheme}
          className="duo-btn duo-btn-ghost w-full justify-start text-sm"
          style={{ textTransform: "none", fontWeight: 700, letterSpacing: "normal", padding: "8px 12px" }}
          title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
        >
          {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
          <span>{theme === "light" ? "Dark Mode" : "Light Mode"}</span>
        </button>
        <button
          onClick={handleLogout}
          className="duo-btn duo-btn-ghost w-full justify-start text-sm"
          style={{ textTransform: "none", fontWeight: 700, letterSpacing: "normal", padding: "8px 12px" }}
        >
          <LogOut size={16} />
          <span>Log Out</span>
        </button>
      </div>
    </>
  );

  return (
    <div className="flex h-screen" style={{ background: "var(--page-bg)" }}>
      <div
        className={`sidebar-overlay lg:hidden ${sidebarOpen ? "open" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      <nav
        className={`
          fixed inset-y-0 left-0 z-50 flex flex-col shrink-0
          transform transition-transform duration-200 ease-in-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        style={{
          width: "240px",
          backgroundColor: "var(--card-bg)",
          borderRight: "2px solid var(--border)",
        }}
      >
        {sidebar}
      </nav>

      <main className="flex-1 overflow-auto" style={{ background: "var(--page-bg)" }}>
        <div
          className="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3"
          style={{
            background: "var(--card-bg)",
            borderBottom: "2px solid var(--border)",
          }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 rounded-lg"
            style={{ color: "var(--text-primary)" }}
            aria-label="Open sidebar"
          >
            <Menu size={20} />
          </button>
          <span style={{ fontSize: "15px", fontWeight: 800, color: "var(--navy)" }}>
            LawFlow
          </span>
        </div>

        <div
          className="mx-auto animate-fade-up"
          style={{
            maxWidth: "760px",
            padding: "var(--space-lg)",
            color: "var(--text-primary)",
          }}
        >
          {children}
        </div>
      </main>
    </div>
  );
}
