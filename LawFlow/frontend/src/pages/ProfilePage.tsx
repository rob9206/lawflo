import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { User, BookOpen, Target, Clock, GraduationCap, FileText, AlertTriangle, RotateCcw, Trash2, Key, Eye, EyeOff, CheckCircle, Settings } from "lucide-react";
import { getProfileStats, getApiKeys, saveApiKeys, resetProgress, resetAll } from "@/api/profile";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const [showResetProgressConfirm, setShowResetProgressConfirm] = useState(false);
  const [showResetAllConfirm, setShowResetAllConfirm] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState("");

  const { data: stats, isLoading } = useQuery({
    queryKey: ["profile-stats"],
    queryFn: getProfileStats,
  });

  const handleResetProgress = async () => {
    setIsResetting(true);
    try {
      await resetProgress();
      await queryClient.invalidateQueries();
      setResetMessage("Progress reset successfully! All study data cleared.");
      setShowResetProgressConfirm(false);
    } catch (error) {
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
      setResetMessage("All data reset successfully! Database completely cleared.");
      setShowResetAllConfirm(false);
    } catch (error) {
      setResetMessage("Failed to reset all data. Please try again.");
    } finally {
      setIsResetting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 rounded-lg w-64" style={{ backgroundColor: "var(--bg-muted)" }} />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl" style={{ backgroundColor: "var(--bg-card)" }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        icon={<User size={24} />}
        title="Profile"
        subtitle="Your study overview and settings"
      />

      {resetMessage && (
        <div
          className="p-4 rounded-lg border"
          style={{
            backgroundColor: resetMessage.includes("Failed") ? "rgba(239, 68, 68, 0.1)" : "rgba(34, 197, 94, 0.1)",
            borderColor: resetMessage.includes("Failed") ? "rgba(239, 68, 68, 0.3)" : "rgba(34, 197, 94, 0.3)",
            color: resetMessage.includes("Failed") ? "#ef4444" : "#22c55e"
          }}
        >
          {resetMessage}
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          icon={<BookOpen size={18} />}
          label="Total Subjects"
          value={String(stats?.total_subjects ?? 0)}
          sub="active courses"
          color="text-blue-400"
        />
        <StatCard
          icon={<Target size={18} />}
          label="Total Topics"
          value={String(stats?.total_topics ?? 0)}
          sub="concepts learned"
          color="text-emerald-400"
        />
        <StatCard
          icon={<Target size={18} />}
          label="Overall Mastery"
          value={`${stats?.overall_mastery ?? 0}%`}
          sub="average score"
          color="text-indigo-400"
        />
        <StatCard
          icon={<Clock size={18} />}
          label="Study Hours"
          value={String(stats?.total_study_hours ?? 0)}
          sub="total time"
          color="text-amber-400"
        />
        <StatCard
          icon={<GraduationCap size={18} />}
          label="Sessions"
          value={String(stats?.total_sessions ?? 0)}
          sub="study sessions"
          color="text-purple-400"
        />
        <StatCard
          icon={<FileText size={18} />}
          label="Documents"
          value={String(stats?.total_documents ?? 0)}
          sub="uploaded files"
          color="text-cyan-400"
        />
      </div>

      {/* API Key Settings */}
      <ApiKeySettings />

      {/* Danger Zone */}
      <Card>
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle size={20} className="text-red-500" />
          <h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            Danger Zone
          </h3>
        </div>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          These actions cannot be undone. Please be certain before proceeding.
        </p>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border" style={{ borderColor: "var(--border)" }}>
            <div>
              <h4 className="font-medium" style={{ color: "var(--text-primary)" }}>Reset Progress</h4>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Clear all study progress, mastery scores, and sessions. Keeps uploaded documents.
              </p>
            </div>
            <button
              onClick={() => setShowResetProgressConfirm(true)}
              disabled={isResetting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
              style={{ backgroundColor: "#f59e0b" }}
            >
              <RotateCcw size={16} />
              Reset Progress
            </button>
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg border" style={{ borderColor: "var(--border)" }}>
            <div>
              <h4 className="font-medium" style={{ color: "var(--text-primary)" }}>Reset All Data</h4>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Complete database wipe. Removes all data including documents, progress, and settings.
              </p>
            </div>
            <button
              onClick={() => setShowResetAllConfirm(true)}
              disabled={isResetting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
              style={{ backgroundColor: "#ef4444" }}
            >
              <Trash2 size={16} />
              Reset All Data
            </button>
          </div>
        </div>
      </Card>

      {/* Reset Progress Confirmation Modal */}
      {showResetProgressConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div
            className="max-w-md w-full mx-4 p-6 rounded-xl border"
            style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
          >
            <h3 className="text-lg font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
              Confirm Reset Progress
            </h3>
            <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
              This will permanently delete all your study progress, mastery scores, sessions, and assessments. 
              Your uploaded documents will be preserved. This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowResetProgressConfirm(false)}
                disabled={isResetting}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-all hover:opacity-90 disabled:opacity-50"
                style={{ 
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                  backgroundColor: "var(--bg-surface)"
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleResetProgress}
                disabled={isResetting}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ backgroundColor: "#f59e0b" }}
              >
                {isResetting ? "Resetting..." : "Reset Progress"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset All Confirmation Modal */}
      {showResetAllConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div
            className="max-w-md w-full mx-4 p-6 rounded-xl border"
            style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
          >
            <h3 className="text-lg font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
              Confirm Reset All Data
            </h3>
            <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
              This will permanently delete ALL data in the database including documents, progress, sessions, 
              assessments, and all other data. This is a complete wipe and cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowResetAllConfirm(false)}
                disabled={isResetting}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-all hover:opacity-90 disabled:opacity-50"
                style={{ 
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                  backgroundColor: "var(--bg-surface)"
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleResetAll}
                disabled={isResetting}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ backgroundColor: "#ef4444" }}
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


// ── API Key Settings Component ──────────────────────────────────────────────

function ApiKeySettings() {
  const queryClient = useQueryClient();
  const [anthropicKey, setAnthropicKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const { data: keyStatus } = useQuery({
    queryKey: ["api-keys"],
    queryFn: getApiKeys,
  });

  const handleSave = async () => {
    if (!anthropicKey.trim()) return;
    setSaving(true);
    setMessage(null);
    try {
      await saveApiKeys({ anthropic_key: anthropicKey.trim() });
      setAnthropicKey("");
      setMessage({ type: "success", text: "API key saved! AI features are now active." });
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    } catch {
      setMessage({ type: "error", text: "Failed to save API key. Please try again." });
    } finally {
      setSaving(false);
    }
  };

  const configured = keyStatus?.anthropic?.configured ?? false;

  return (
    <Card>
      <div className="flex items-center gap-3 mb-4">
        <Settings size={20} className="text-indigo-400" />
        <h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
          API Configuration
        </h3>
        {configured && (
          <span className="ml-auto flex items-center gap-1.5 text-xs font-medium text-emerald-400">
            <CheckCircle size={14} />
            Connected
          </span>
        )}
      </div>

      <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
        LawFlow uses Claude AI for document processing, tutoring, exam generation, and study plans.
        Enter your Anthropic API key to enable all features.
      </p>

      {message && (
        <div
          className="p-3 rounded-lg border text-sm mb-4"
          style={{
            backgroundColor: message.type === "error" ? "rgba(239,68,68,0.1)" : "rgba(34,197,94,0.1)",
            borderColor: message.type === "error" ? "rgba(239,68,68,0.3)" : "rgba(34,197,94,0.3)",
            color: message.type === "error" ? "#ef4444" : "#22c55e",
          }}
        >
          {message.text}
        </div>
      )}

      {/* Current key status */}
      {configured && keyStatus?.anthropic?.masked && (
        <div
          className="flex items-center gap-3 p-3 rounded-lg mb-4"
          style={{ backgroundColor: "var(--bg-muted)" }}
        >
          <Key size={16} className="text-ui-muted shrink-0" />
          <span className="text-sm font-mono text-ui-muted">{keyStatus.anthropic.masked}</span>
          <span className="text-xs text-ui-muted ml-auto">
            Model: {keyStatus.anthropic.model}
          </span>
        </div>
      )}

      {!configured && (
        <div
          className="flex items-center gap-3 p-3 rounded-lg border mb-4"
          style={{
            backgroundColor: "rgba(245,158,11,0.08)",
            borderColor: "rgba(245,158,11,0.3)",
          }}
        >
          <AlertTriangle size={16} className="text-amber-400 shrink-0" />
          <span className="text-sm text-amber-400">
            No API key configured — AI features are disabled.
          </span>
        </div>
      )}

      {/* Key input */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <input
            type={showKey ? "text" : "password"}
            value={anthropicKey}
            onChange={(e) => setAnthropicKey(e.target.value)}
            placeholder={configured ? "Enter new key to replace…" : "sk-ant-…"}
            className="input-base w-full rounded-lg px-3 py-2.5 pr-10 text-sm font-mono"
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-ui-muted hover:text-ui-primary transition-colors"
          >
            {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        <button
          onClick={handleSave}
          disabled={!anthropicKey.trim() || saving}
          className="btn-primary px-5 py-2.5 text-sm disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save Key"}
        </button>
      </div>

      <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
        Your key is stored locally in the <code className="px-1 py-0.5 rounded" style={{ backgroundColor: "var(--bg-muted)" }}>.env</code> file and never leaves your machine.
        Get a key at{" "}
        <a
          href="https://console.anthropic.com/settings/keys"
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-400 underline underline-offset-2"
        >
          console.anthropic.com
        </a>
      </p>
    </Card>
  );
}