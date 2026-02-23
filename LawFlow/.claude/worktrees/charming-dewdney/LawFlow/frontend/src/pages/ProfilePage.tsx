import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { User, BookOpen, Target, Clock, GraduationCap, FileText, AlertTriangle, RotateCcw, Trash2, Key } from "lucide-react";
import { getProfileStats, resetProgress, resetAll } from "@/api/profile";
import { clearApiKey, getStoredApiKey, looksLikeAnthropicKey, maskApiKey, saveApiKey } from "@/lib/apiKey";
import Card from "@/components/ui/Card";
import StatCard from "@/components/ui/StatCard";
import PageHeader from "@/components/ui/PageHeader";

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const [showResetProgressConfirm, setShowResetProgressConfirm] = useState(false);
  const [showResetAllConfirm, setShowResetAllConfirm] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState(() => getStoredApiKey());
  const [savedApiKey, setSavedApiKey] = useState(() => getStoredApiKey());
  const [apiKeyMessage, setApiKeyMessage] = useState("");

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
      <PageHeader
        icon={<User size={24} />}
        title="Profile"
        subtitle="Your study overview and settings"
      />

      {/* Profile Header */}
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
              Law Student
            </h3>
            <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-secondary)" }}>
              LawFlow Learner
            </p>
          </div>
        </div>
      </div>

      <div className="duo-card p-5">
        <div className="flex items-center gap-3 mb-3">
          <Key size={18} style={{ color: "var(--blue)" }} />
          <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
            Anthropic API Key
          </h3>
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
          <button
            onClick={handleSaveApiKey}
            className="duo-btn duo-btn-green"
          >
            Save Key
          </button>
          <button
            onClick={handleClearApiKey}
            className="duo-btn duo-btn-outline"
          >
            Clear
          </button>
        </div>
        <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-muted)", marginTop: 10 }}>
          Current key:{" "}
          <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>
            {maskApiKey(savedApiKey)}
          </span>
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

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          icon={<BookOpen size={18} />}
          label="Total Subjects"
          value={String(stats?.total_subjects ?? 0)}
          sub="active courses"
          color="var(--blue)"
        />
        <StatCard
          icon={<Target size={18} />}
          label="Total Topics"
          value={String(stats?.total_topics ?? 0)}
          sub="concepts learned"
          color="var(--green)"
        />
        <StatCard
          icon={<Target size={18} />}
          label="Overall Mastery"
          value={`${stats?.overall_mastery ?? 0}%`}
          sub="average score"
          color="var(--purple)"
        />
        <StatCard
          icon={<Clock size={18} />}
          label="Study Hours"
          value={String(stats?.total_study_hours ?? 0)}
          sub="total time"
          color="var(--orange)"
        />
        <StatCard
          icon={<GraduationCap size={18} />}
          label="Sessions"
          value={String(stats?.total_sessions ?? 0)}
          sub="study sessions"
          color="var(--purple)"
        />
        <StatCard
          icon={<FileText size={18} />}
          label="Documents"
          value={String(stats?.total_documents ?? 0)}
          sub="uploaded files"
          color="var(--blue)"
        />
      </div>

      {/* Danger Zone */}
      <div
        className="duo-card p-5"
        style={{ backgroundColor: "var(--red-bg)", borderColor: "var(--red)" }}
      >
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle size={20} style={{ color: "var(--red)" }} />
          <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
            Danger Zone
          </h3>
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
                Clear all study progress, mastery scores, and sessions. Keeps uploaded documents.
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
                Complete database wipe. Removes all data including documents, progress, and settings.
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

      {/* Reset Progress Confirmation Modal */}
      {showResetProgressConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="duo-card max-w-md w-full mx-4 p-6">
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16, color: "var(--text-primary)" }}>
              Confirm Reset Progress
            </h3>
            <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 24, color: "var(--text-muted)" }}>
              This will permanently delete all your study progress, mastery scores, sessions, and assessments.
              Your uploaded documents will be preserved. This action cannot be undone.
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

      {/* Reset All Confirmation Modal */}
      {showResetAllConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="duo-card max-w-md w-full mx-4 p-6">
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16, color: "var(--text-primary)" }}>
              Confirm Reset All Data
            </h3>
            <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 24, color: "var(--text-muted)" }}>
              This will permanently delete ALL data in the database including documents, progress, sessions,
              assessments, and all other data. This is a complete wipe and cannot be undone.
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
