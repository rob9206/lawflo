import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div
            className="w-6 h-6 rounded-full border-3 border-t-transparent animate-spin"
            style={{ borderColor: "var(--blue)", borderTopColor: "transparent" }}
          />
          <span style={{ color: "var(--text-muted)", fontSize: "15px", fontWeight: 600 }}>
            Loading account...
          </span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }

  return <>{children}</>;
}
