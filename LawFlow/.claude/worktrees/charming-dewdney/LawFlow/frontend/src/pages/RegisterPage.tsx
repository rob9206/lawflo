import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { UserPlus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import Card from "@/components/ui/Card";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { register } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await register(email.trim(), password, displayName.trim() || undefined);
      const next = searchParams.get("next");
      navigate(next || "/dashboard", { replace: true });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: "var(--page-bg)" }}>
      <Card className="w-full max-w-md" padding="lg">
        <div className="flex items-center gap-2 mb-6">
          <UserPlus size={20} style={{ color: "var(--green)" }} />
          <h1 style={{ fontSize: "24px", fontWeight: 900, color: "var(--text-primary)" }}>Create Account</h1>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="duo-label">Display Name</label>
            <input
              className="duo-input w-full"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Law Student"
              autoComplete="name"
            />
          </div>
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
              minLength={8}
              autoComplete="new-password"
            />
            <p style={{ color: "var(--text-muted)", fontWeight: 600, fontSize: "12px", marginTop: "6px" }}>
              Must be at least 8 characters.
            </p>
          </div>
          {error && (
            <div className="duo-card p-3" style={{ background: "var(--red-bg)", borderColor: "var(--red)" }}>
              <p style={{ color: "var(--red)", fontWeight: 700, fontSize: "14px" }}>{error}</p>
            </div>
          )}
          <button type="submit" className="duo-btn duo-btn-green w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create Account"}
          </button>
        </form>
        <p className="mt-4" style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: 600 }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "var(--blue)", fontWeight: 800 }}>
            Log in
          </Link>
        </p>
      </Card>
    </div>
  );
}
