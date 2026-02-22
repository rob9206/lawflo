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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      role="dialog"
      aria-modal="true"
      aria-label="LawFlow introduction tutorial"
    >
      <div
        className="w-full max-w-lg rounded-2xl p-6"
        style={{
          backgroundColor: "var(--bg-card)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-card)",
        }}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {slides.map((_, i) => (
              <span
                key={i}
                className="h-1.5 w-8 rounded-full transition-all"
                style={{
                  backgroundColor: i === index ? "var(--accent)" : "var(--bg-muted)",
                }}
              />
            ))}
          </div>
          <button
            onClick={closeTutorial}
            className="rounded-lg p-1.5 transition-colors"
            style={{ color: "var(--text-muted)" }}
            aria-label="Close tutorial"
          >
            <X size={16} />
          </button>
        </div>

        <div key={index} className="min-h-52 animate-in fade-in duration-200">
          <div className="mb-4 inline-flex rounded-xl p-3" style={{ backgroundColor: "var(--accent-muted)" }}>
            <slide.icon size={20} />
          </div>

          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Step {index + 1} of {slides.length}
          </p>
          <h2 className="mt-1 text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            {slide.title}
          </h2>
          <p className="mt-1 text-sm" style={{ color: "var(--accent-text)" }}>
            {slide.subtitle}
          </p>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {slide.description}
          </p>
        </div>

        <div className="mt-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={closeTutorial}
              className="rounded-lg px-3 py-2 text-sm"
              style={{ color: "var(--text-muted)" }}
            >
              Skip
            </button>
            <button
              onClick={handleBack}
              disabled={index === 0}
              className="rounded-lg px-3 py-2 text-sm disabled:opacity-50"
              style={{ color: "var(--text-secondary)" }}
            >
              Back
            </button>
          </div>

          {isLastSlide ? (
            <button
              ref={nextButtonRef}
              onClick={handleFinish}
              className="rounded-lg px-4 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: "var(--accent)" }}
            >
              Start AutoTeach
            </button>
          ) : (
            <button
              ref={nextButtonRef}
              onClick={handleNext}
              className="rounded-lg px-4 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: "var(--accent)" }}
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
