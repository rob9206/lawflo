import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { LogIn } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import Card from "@/components/ui/Card";

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email.trim(), password);
      const next = searchParams.get("next");
      navigate(next || "/dashboard", { replace: true });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: "var(--page-bg)" }}>
      <Card className="w-full max-w-md" padding="lg">
        <div className="flex items-center gap-2 mb-6">
          <LogIn size={20} style={{ color: "var(--blue)" }} />
          <h1 style={{ fontSize: "24px", fontWeight: 900, color: "var(--text-primary)" }}>Log In</h1>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="duo-label">Email</label>
            <input
              className="duo-input w-full"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div>
            <label className="duo-label">Password</label>
            <input
              className="duo-input w-full"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          {error && (
            <div className="duo-card p-3" style={{ background: "var(--red-bg)", borderColor: "var(--red)" }}>
              <p style={{ color: "var(--red)", fontWeight: 700, fontSize: "14px" }}>{error}</p>
            </div>
          )}
          <button type="submit" className="duo-btn duo-btn-blue w-full" disabled={isSubmitting}>
            {isSubmitting ? "Logging in..." : "Log In"}
          </button>
        </form>
        <p className="mt-4" style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: 600 }}>
          No account yet?{" "}
          <Link to="/register" style={{ color: "var(--blue)", fontWeight: 800 }}>
            Create one
          </Link>
        </p>
      </Card>
    </div>
  );
}
