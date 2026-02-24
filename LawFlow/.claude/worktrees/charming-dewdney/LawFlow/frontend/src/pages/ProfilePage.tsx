import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  Clock,
  Crown,
  FileText,
  GraduationCap,
  Key,
  Lock,
  Mail,
  RotateCcw,
  Target,
  Trash2,
  User,
} from "lucide-react";
import { getProfileStats, resetAll, resetProgress } from "@/api/profile";
import { createCheckout, createPortal, getBillingStatus } from "@/api/billing";
import {
  clearApiKey,
  getStoredApiKey,
  looksLikeAnthropicKey,
  maskApiKey,
  saveApiKey,
} from "@/lib/apiKey";
import { useAuth } from "@/context/AuthContext";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";

export default function ProfilePage() {
  const { user, isPro, updateProfile, changePassword } = useAuth();
  const queryClient = useQueryClient();

  const [showResetProgressConfirm, setShowResetProgressConfirm] = useState(false);
  const [showResetAllConfirm, setShowResetAllConfirm] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState("");

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [profileMessage, setProfileMessage] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");

  const [isBillingBusy, setIsBillingBusy] = useState(false);
  const [billingMessage, setBillingMessage] = useState("");

  const [apiKeyInput, setApiKeyInput] = useState(() => getStoredApiKey());
  const [savedApiKey, setSavedApiKey] = useState(() => getStoredApiKey());
  const [apiKeyMessage, setApiKeyMessage] = useState("");

  useEffect(() => {
    setDisplayName(user?.display_name ?? "");
  }, [user?.display_name]);

  const { data: stats, isLoading } = useQuery({
    queryKey: ["profile-stats"],
    queryFn: getProfileStats,
  });

  const { data: billing } = useQuery({
    queryKey: ["billing-status"],
    queryFn: getBillingStatus,
  });

  const handleSaveProfile = async () => {
    const value = displayName.trim();
    if (!value) {
      setProfileMessage("Display name cannot be empty.");
      return;
    }
    setProfileMessage("");
    setIsSavingProfile(true);
    try {
      await updateProfile({ display_name: value });
      setProfileMessage("Profile updated.");
    } catch {
      setProfileMessage("Failed to update profile.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangePassword = async () => {
    setPasswordMessage("");
    if (!currentPassword || !newPassword) {
      setPasswordMessage("Enter both current and new password.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordMessage("New password must be at least 8 characters.");
      return;
    }
    setIsSavingProfile(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setPasswordMessage("Password changed successfully.");
    } catch {
      setPasswordMessage("Failed to change password.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleBillingAction = async () => {
    setBillingMessage("");
    setIsBillingBusy(true);
    try {
      if (isPro) {
        const portal = await createPortal();
        window.location.href = portal.url;
      } else {
        const checkout = await createCheckout();
        window.location.href = checkout.url;
      }
    } catch {
      setBillingMessage("Unable to open billing flow. Check Stripe configuration.");
      setIsBillingBusy(false);
    }
  };

  const handleResetProgress = async () => {
    setIsResetting(true);
    try {
      await resetProgress();
      await queryClient.invalidateQueries();
      setResetMessage("Progress reset successfully.");
      setShowResetProgressConfirm(false);
    } catch {
      setResetMessage("Failed to reset progress. Please try again.");
    } finally {
      setIsResetting(false);
    }
  };

  const handleResetAll = async () => {
    setIsResetting(true);
    try {
      await resetAll();
      await queryClient.invalidateQueries();
      setResetMessage("All your account data was reset successfully.");
      setShowResetAllConfirm(false);
    } catch {
      setResetMessage("Failed to reset all data. Please try again.");
    } finally {
      setIsResetting(false);
    }
  };

  const handleSaveApiKey = () => {
    const normalized = saveApiKey(apiKeyInput);
    setApiKeyInput(normalized);
    setSavedApiKey(normalized);

    if (!normalized) {
      setApiKeyMessage("Saved key cleared.");
      return;
    }

    if (!looksLikeAnthropicKey(normalized)) {
      setApiKeyMessage("Key saved, but format looks unusual (Anthropic keys usually start with sk-ant-).");
      return;
    }

    setApiKeyMessage("API key saved. New tutor requests will use this key.");
  };

  const handleClearApiKey = () => {
    clearApiKey();
    setApiKeyInput("");
    setSavedApiKey("");
    setApiKeyMessage("Saved key cleared.");
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 rounded-lg w-64" style={{ backgroundColor: "var(--surface-bg)" }} />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl" style={{ backgroundColor: "var(--card-bg)" }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader icon={<User size={24} />} title="Profile" subtitle="Your account, billing, and study settings" />

      <div className="duo-card p-5">
        <div className="flex items-center gap-4">
          <div
            className="flex items-center justify-center"
            style={{
              width: 64,
              height: 64,
              borderRadius: "50%",
              border: "2px solid var(--blue)",
              backgroundColor: "var(--blue-bg)",
              color: "var(--blue)",
            }}
          >
            <User size={28} />
          </div>
          <div>
            <h3 style={{ fontSize: 22, fontWeight: 900, color: "var(--text-primary)" }}>
              {user?.display_name ?? "Law Student"}
            </h3>
            <p className="inline-flex items-center gap-1" style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)" }}>
              <Mail size={14} />
              {user?.email ?? "No email"}
            </p>
            <div className="mt-2">
              <span className={isPro ? "duo-badge duo-badge-gold" : "duo-badge duo-badge-blue"}>
                {isPro ? "PRO" : "FREE"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="duo-card p-5 space-y-4">
        <div className="flex items-center gap-3">
          <User size={18} style={{ color: "var(--blue)" }} />
          <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
            Account Settings
          </h3>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="duo-label">Display Name</label>
            <input className="duo-input w-full" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </div>
          <div className="flex items-end">
            <button onClick={handleSaveProfile} className="duo-btn duo-btn-blue w-full" disabled={isSavingProfile}>
              {isSavingProfile ? "Saving..." : "Save Profile"}
            </button>
          </div>
        </div>
        {profileMessage && (
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-muted)" }}>{profileMessage}</p>
        )}
      </div>

      <div className="duo-card p-5 space-y-3">
        <div className="flex items-center gap-3">
          <Lock size={18} style={{ color: "var(--purple)" }} />
          <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
            Change Password
          </h3>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <input
            className="duo-input"
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <input
            className="duo-input"
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
        </div>
        <button onClick={handleChangePassword} disabled={isSavingProfile} className="duo-btn duo-btn-outline">
          {isSavingProfile ? "Saving..." : "Update Password"}
        </button>
        {passwordMessage && (
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-muted)" }}>{passwordMessage}</p>
        )}
      </div>

      <div className="duo-card p-5 space-y-3">
        <div className="flex items-center gap-3">
          <Crown size={18} style={{ color: "var(--gold)" }} />
          <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
            Subscription
          </h3>
        </div>
        <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-secondary)" }}>
          Current tier: <span style={{ color: "var(--text-primary)" }}>{(billing?.tier || stats?.tier || "free").toUpperCase()}</span>
          {billing?.subscription_status ? ` (${billing.subscription_status})` : ""}
        </p>
        {!isPro && billing?.limits && (
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-muted)" }}>
            <p>Tutor sessions: {billing.usage.tutor_sessions_daily}/{billing.limits.tutor_sessions_daily}</p>
            <p>Exam generations: {billing.usage.exam_generations_daily}/{billing.limits.exam_generations_daily}</p>
            <p>Documents: {billing.usage.document_uploads_total}/{billing.limits.document_uploads_total}</p>
          </div>
        )}
        <button onClick={handleBillingAction} disabled={isBillingBusy} className="duo-btn duo-btn-green">
          {isBillingBusy ? "Opening..." : isPro ? "Manage Subscription" : "Upgrade to Pro"}
        </button>
        {billingMessage && (
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--red)" }}>{billingMessage}</p>
        )}
      </div>

      <div className="duo-card p-5">
        <div className="flex items-center gap-3 mb-3">
          <Key size={18} style={{ color: "var(--blue)" }} />
          <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>Anthropic API Key</h3>
        </div>
        <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-muted)", marginBottom: 12 }}>
          Stored locally in this browser and sent only to your LawFlow backend.
        </p>
        <div className="flex flex-wrap gap-2">
          <input
            type="password"
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleSaveApiKey();
              }
            }}
            placeholder="sk-ant-..."
            autoComplete="off"
            className="duo-input flex-1"
            style={{ minWidth: 320 }}
          />
          <button onClick={handleSaveApiKey} className="duo-btn duo-btn-green">Save Key</button>
          <button onClick={handleClearApiKey} className="duo-btn duo-btn-outline">Clear</button>
        </div>
        <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-muted)", marginTop: 10 }}>
          Current key:{" "}
          <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>{maskApiKey(savedApiKey)}</span>
        </p>
        {apiKeyMessage && (
          <p
            style={{
              fontSize: 13,
              fontWeight: 600,
              marginTop: 8,
              color: apiKeyMessage.includes("unusual") ? "var(--orange)" : "var(--green)",
            }}
          >
            {apiKeyMessage}
          </p>
        )}
      </div>

      {resetMessage && (
        <div
          className="duo-card p-4"
          style={{
            backgroundColor: resetMessage.includes("Failed") ? "var(--red-bg)" : "var(--green-bg)",
            borderColor: resetMessage.includes("Failed") ? "var(--red)" : "var(--green)",
            color: resetMessage.includes("Failed") ? "var(--red)" : "var(--green)",
          }}
        >
          {resetMessage}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard icon={<BookOpen size={18} />} label="Total Subjects" value={String(stats?.total_subjects ?? 0)} sub="active courses" color="var(--blue)" />
        <StatCard icon={<Target size={18} />} label="Total Topics" value={String(stats?.total_topics ?? 0)} sub="concepts learned" color="var(--green)" />
        <StatCard icon={<Target size={18} />} label="Overall Mastery" value={`${stats?.overall_mastery ?? 0}%`} sub="average score" color="var(--purple)" />
        <StatCard icon={<Clock size={18} />} label="Study Hours" value={String(stats?.total_study_hours ?? 0)} sub="total time" color="var(--orange)" />
        <StatCard icon={<GraduationCap size={18} />} label="Sessions" value={String(stats?.total_sessions ?? 0)} sub="study sessions" color="var(--purple)" />
        <StatCard icon={<FileText size={18} />} label="Documents" value={String(stats?.total_documents ?? 0)} sub="uploaded files" color="var(--blue)" />
      </div>

      <div className="duo-card p-5" style={{ backgroundColor: "var(--red-bg)", borderColor: "var(--red)" }}>
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle size={20} style={{ color: "var(--red)" }} />
          <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>Danger Zone</h3>
        </div>
        <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 24, color: "var(--text-muted)" }}>
          These actions cannot be undone. Please be certain before proceeding.
        </p>

        <div className="space-y-4">
          <div
            className="flex items-center justify-between p-4 rounded-lg"
            style={{ backgroundColor: "var(--card-bg)", border: "2px solid var(--border)" }}
          >
            <div>
              <h4 style={{ fontWeight: 700, color: "var(--text-primary)" }}>Reset Progress</h4>
              <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-muted)" }}>
                Clear study progress, mastery scores, and sessions. Keeps uploaded documents.
              </p>
            </div>
            <button
              onClick={() => setShowResetProgressConfirm(true)}
              disabled={isResetting}
              className="duo-btn duo-btn-red flex items-center gap-2"
              style={{ opacity: isResetting ? 0.5 : 1 }}
            >
              <RotateCcw size={16} />
              Reset Progress
            </button>
          </div>

          <div
            className="flex items-center justify-between p-4 rounded-lg"
            style={{ backgroundColor: "var(--card-bg)", border: "2px solid var(--border)" }}
          >
            <div>
              <h4 style={{ fontWeight: 700, color: "var(--text-primary)" }}>Reset All Data</h4>
              <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-muted)" }}>
                Delete all data in your account, including documents and progress.
              </p>
            </div>
            <button
              onClick={() => setShowResetAllConfirm(true)}
              disabled={isResetting}
              className="duo-btn duo-btn-red flex items-center gap-2"
              style={{ opacity: isResetting ? 0.5 : 1 }}
            >
              <Trash2 size={16} />
              Reset All Data
            </button>
          </div>
        </div>
      </div>

      {showResetProgressConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="duo-card max-w-md w-full mx-4 p-6">
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16, color: "var(--text-primary)" }}>
              Confirm Reset Progress
            </h3>
            <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 24, color: "var(--text-muted)" }}>
              This will permanently delete your study progress, mastery scores, sessions, and assessments.
              Uploaded documents are preserved.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowResetProgressConfirm(false)}
                disabled={isResetting}
                className="duo-btn duo-btn-outline flex-1"
                style={{ opacity: isResetting ? 0.5 : 1 }}
              >
                Cancel
              </button>
              <button
                onClick={handleResetProgress}
                disabled={isResetting}
                className="duo-btn duo-btn-red flex-1"
                style={{ opacity: isResetting ? 0.5 : 1 }}
              >
                {isResetting ? "Resetting..." : "Reset Progress"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showResetAllConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="duo-card max-w-md w-full mx-4 p-6">
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16, color: "var(--text-primary)" }}>
              Confirm Reset All Data
            </h3>
            <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 24, color: "var(--text-muted)" }}>
              This permanently deletes all data in your account including documents, progress, sessions, and assessments.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowResetAllConfirm(false)}
                disabled={isResetting}
                className="duo-btn duo-btn-outline flex-1"
                style={{ opacity: isResetting ? 0.5 : 1 }}
              >
                Cancel
              </button>
              <button
                onClick={handleResetAll}
                disabled={isResetting}
                className="duo-btn duo-btn-red flex-1"
                style={{ opacity: isResetting ? 0.5 : 1 }}
              >
                {isResetting ? "Resetting..." : "Reset All Data"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
