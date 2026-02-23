import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart2, Sparkles, Upload, X, Zap } from "lucide-react";
import { useTutorial } from "@/context/TutorialContext";

type Slide = {
  title: string;
  subtitle: string;
  description: string;
  icon: React.ComponentType<{ size?: number }>;
};

const slides: Slide[] = [
  {
    title: "Welcome to LawFlow",
    subtitle: "Your AI-powered law school study engine",
    description:
      "We will show you how AI helps you focus on the right topics, practice faster, and improve where it matters most.",
    icon: Sparkles,
  },
  {
    title: "AutoTeach",
    subtitle: "Study what matters first",
    description:
      "LawFlow combines your weakest topics with exam weighting to auto-pick your next best study target and teaching mode.",
    icon: Zap,
  },
  {
    title: "Upload your materials",
    subtitle: "Grounded in your real class content",
    description:
      "Upload outlines, notes, and past exams. The AI uses your documents to deliver context-aware explanations and drills.",
    icon: Upload,
  },
  {
    title: "Track your mastery",
    subtitle: "See strengths and gaps clearly",
    description:
      "Every session updates mastery by topic so your dashboard and study plan stay aligned with your progress.",
    icon: BarChart2,
  },
  {
    title: "Ready to start",
    subtitle: "Launch your first AI-guided session",
    description:
      "Go to AutoTeach and let LawFlow choose the highest-impact topic to work on first.",
    icon: Zap,
  },
];

export default function TutorialModal() {
  const navigate = useNavigate();
  const { isOpen, closeTutorial } = useTutorial();
  const [index, setIndex] = useState(0);
  const nextButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeTutorial();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, closeTutorial]);

  useEffect(() => {
    if (!isOpen) return;
    nextButtonRef.current?.focus();
  }, [isOpen, index]);

  const isLastSlide = index === slides.length - 1;
  const slide = useMemo(() => slides[index], [index]);

  if (!isOpen) return null;

  const handleBack = () => setIndex((i) => Math.max(0, i - 1));
  const handleNext = () => setIndex((i) => Math.min(slides.length - 1, i + 1));

  const handleFinish = () => {
    closeTutorial();
    navigate("/auto-teach");
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: "rgba(0,0,0,0.3)", backdropFilter: "blur(4px)" }}
      role="dialog"
      aria-modal="true"
      aria-label="LawFlow introduction tutorial"
    >
      <div
        className="duo-card w-full animate-scale-in"
        style={{
          maxWidth: "480px",
          padding: "28px",
          borderRadius: "var(--radius-xl)",
        }}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {slides.map((_, i) => (
              <span
                key={i}
                className="h-1.5 w-8 rounded-full transition-all"
                style={{
                  backgroundColor: i === index ? "var(--blue)" : "var(--border)",
                }}
              />
            ))}
          </div>
          <button
            onClick={closeTutorial}
            className="duo-btn duo-btn-ghost p-1.5"
            style={{ textTransform: "none", padding: "6px" }}
            aria-label="Close tutorial"
          >
            <X size={16} />
          </button>
        </div>

        <div key={index} className="min-h-52 animate-fade-in">
          <div
            className="mb-4 inline-flex p-3"
            style={{
              backgroundColor: "var(--blue-bg)",
              borderRadius: "var(--radius-md)",
              color: "var(--blue)",
            }}
          >
            <slide.icon size={20} />
          </div>

          <p style={{
            fontSize: "11px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--text-muted)",
          }}>
            Step {index + 1} of {slides.length}
          </p>
          <h2 style={{ marginTop: "4px", fontSize: "22px", fontWeight: 900, color: "var(--text-primary)" }}>
            {slide.title}
          </h2>
          <p style={{ marginTop: "4px", fontSize: "15px", fontWeight: 600, color: "var(--blue-dark)" }}>
            {slide.subtitle}
          </p>
          <p style={{ marginTop: "16px", fontSize: "15px", fontWeight: 500, lineHeight: 1.6, color: "var(--text-secondary)" }}>
            {slide.description}
          </p>
        </div>

        <div className="mt-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={closeTutorial}
              className="duo-btn duo-btn-ghost"
              style={{ textTransform: "none", fontWeight: 600, fontSize: "14px", padding: "8px 12px" }}
            >
              Skip
            </button>
            <button
              onClick={handleBack}
              disabled={index === 0}
              className="duo-btn duo-btn-ghost disabled:opacity-50"
              style={{ textTransform: "none", fontWeight: 600, fontSize: "14px", padding: "8px 12px" }}
            >
              Back
            </button>
          </div>

          {isLastSlide ? (
            <button
              ref={nextButtonRef}
              onClick={handleFinish}
              className="duo-btn duo-btn-green"
            >
              Start AutoTeach
            </button>
          ) : (
            <button
              ref={nextButtonRef}
              onClick={handleNext}
              className="duo-btn duo-btn-blue"
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
