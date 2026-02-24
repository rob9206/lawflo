import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Check, Crown } from "lucide-react";
import { createCheckout, createPortal, getBillingStatus } from "@/api/billing";
import { useAuth } from "@/context/AuthContext";
import Card from "@/components/ui/Card";

const featureRows = [
  { name: "AI tutor sessions", free: "5/day", pro: "Unlimited" },
  { name: "Document uploads", free: "10 total", pro: "Unlimited" },
  { name: "Exam simulations", free: "3/day", pro: "Unlimited" },
  { name: "Flashcard generation", free: "20/day", pro: "Unlimited" },
  { name: "AutoTeach", free: "Limited", pro: "Full access" },
];

export default function PricingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isPro } = useAuth();
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState("");

  const { data: billing } = useQuery({
    queryKey: ["billing-status"],
    queryFn: getBillingStatus,
    enabled: isAuthenticated,
  });

  const handleUpgrade = async () => {
    if (!isAuthenticated) {
      navigate("/login?next=%2Fpricing");
      return;
    }
    setError("");
    setIsBusy(true);
    try {
      const data = await createCheckout();
      window.location.href = data.url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start checkout");
    } finally {
      setIsBusy(false);
    }
  };

  const handleManage = async () => {
    setError("");
    setIsBusy(true);
    try {
      const data = await createPortal();
      window.location.href = data.url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to open billing portal");
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <div className="min-h-screen py-10 px-4" style={{ background: "var(--page-bg)" }}>
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="text-center space-y-2">
          <h1 style={{ fontSize: "36px", fontWeight: 900, color: "var(--text-primary)" }}>
            Choose Your Plan
          </h1>
          <p style={{ color: "var(--text-muted)", fontWeight: 600, fontSize: "16px" }}>
            Start free, upgrade when you need deeper practice and unlimited access.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <Card padding="lg">
            <h2 style={{ fontSize: "22px", fontWeight: 900, color: "var(--text-primary)" }}>Free</h2>
            <p style={{ color: "var(--text-muted)", fontWeight: 700, marginBottom: "14px" }}>Great for getting started</p>
            <ul className="space-y-2">
              {featureRows.map((row) => (
                <li key={row.name} className="flex items-center gap-2">
                  <Check size={16} style={{ color: "var(--green)" }} />
                  <span style={{ color: "var(--text-secondary)", fontWeight: 700, fontSize: "14px" }}>
                    {row.name}: {row.free}
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card padding="lg" className="relative" style={{ borderColor: "var(--gold)" }}>
            <div className="absolute -top-3 right-4 duo-badge duo-badge-gold">Most Popular</div>
            <div className="flex items-center gap-2">
              <Crown size={20} style={{ color: "var(--gold)" }} />
              <h2 style={{ fontSize: "22px", fontWeight: 900, color: "var(--text-primary)" }}>Pro</h2>
            </div>
            <p style={{ color: "var(--text-muted)", fontWeight: 700, marginBottom: "14px" }}>
              Unlimited practice and faster progress
            </p>
            <ul className="space-y-2">
              {featureRows.map((row) => (
                <li key={row.name} className="flex items-center gap-2">
                  <Check size={16} style={{ color: "var(--green)" }} />
                  <span style={{ color: "var(--text-secondary)", fontWeight: 700, fontSize: "14px" }}>
                    {row.name}: {row.pro}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        {billing && (
          <Card padding="md">
            <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-secondary)" }}>
              Current tier: <span style={{ color: "var(--text-primary)" }}>{billing.tier.toUpperCase()}</span>
              {" "}({billing.subscription_status})
            </p>
          </Card>
        )}

        {error && (
          <Card padding="md" style={{ background: "var(--red-bg)", borderColor: "var(--red)" }}>
            <p style={{ color: "var(--red)", fontWeight: 700 }}>{error}</p>
          </Card>
        )}

        <div className="flex gap-3 justify-center">
          {!isPro ? (
            <button className="duo-btn duo-btn-green" onClick={handleUpgrade} disabled={isBusy}>
              {isBusy ? "Working..." : "Upgrade to Pro"}
            </button>
          ) : (
            <button className="duo-btn duo-btn-outline" onClick={handleManage} disabled={isBusy}>
              {isBusy ? "Opening..." : "Manage Subscription"}
            </button>
          )}
          <Link to={isAuthenticated ? "/dashboard" : "/"} className="duo-btn duo-btn-outline">
            Back
          </Link>
        </div>
      </div>
    </div>
  );
}
