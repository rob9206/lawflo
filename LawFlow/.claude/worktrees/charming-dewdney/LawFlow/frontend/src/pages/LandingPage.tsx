import { useNavigate } from "react-router-dom";
import {
  Scale,
  Brain,
  Target,
  Upload,
  Check,
  ChevronRight,
  Sparkles,
  GraduationCap,
  Shield,
  Award,
} from "lucide-react";
import Card from "@/components/ui/Card";
import { useAuth } from "@/context/AuthContext";

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const handleGetStarted = () => {
    navigate(isAuthenticated ? "/dashboard" : "/register");
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "var(--page-bg)", color: "var(--text-primary)" }}>
      {/* Navigation Bar */}
      <nav
        className="sticky top-0 z-50 backdrop-blur-md"
        style={{
          backgroundColor: "var(--page-bg)",
          borderBottom: "2px solid var(--border)",
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-6 h-6" style={{ color: "var(--green)" }} />
            <span style={{ fontSize: "22px", fontWeight: 900, color: "var(--text-primary)" }}>LawFlow</span>
          </div>
          <button
            onClick={handleGetStarted}
            className="duo-btn duo-btn-green"
            style={{ padding: "8px 16px", fontSize: "15px" }}
          >
            {isAuthenticated ? "Open App" : "Get Started"}
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="flex-1 min-h-screen flex items-center py-12 md:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            {/* Left Column */}
            <div className="space-y-6 animate-fade-in">
              <h1 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 900, lineHeight: 1.1, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
                Master Law School. Efficiently.
              </h1>

              <p style={{ fontSize: "18px", fontWeight: 500, lineHeight: 1.6, maxWidth: "540px", color: "var(--text-secondary)" }}>
                Stop falling behind. Get AI tutoring that knows exactly where
                you're struggling and drills you on what actually shows up on
                exams.
              </p>

              <button
                onClick={handleGetStarted}
                className="duo-btn duo-btn-green group"
                style={{ padding: "12px 24px", fontSize: "18px", display: "inline-flex", alignItems: "center", gap: "8px" }}
              >
                Get Started Free
                <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </button>

              {/* Trust Indicators */}
              <div className="space-y-3 pt-4">
                <div className="flex items-center gap-3">
                  <Check className="w-5 h-5 flex-shrink-0" style={{ color: "var(--green)" }} />
                  <span style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>Free to start</span>
                </div>
                <div className="flex items-center gap-3">
                  <Check className="w-5 h-5 flex-shrink-0" style={{ color: "var(--green)" }} />
                  <span style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
                    No credit card required
                  </span>
                </div>
              </div>
            </div>

            {/* Right Column - Decorative Card */}
            <div className="hidden lg:flex items-center justify-center animate-fade-in">
              <div className="relative w-full max-w-md">
                {/* Gradient Background */}
                <div
                  className="absolute inset-0 blur-3xl"
                  style={{
                    borderRadius: "var(--radius-xl)",
                    background: "linear-gradient(135deg, var(--green-bg), transparent)",
                  }}
                />

                {/* Mock Study Session Card */}
                <Card
                  padding="none"
                  className="relative overflow-hidden"
                  style={{ border: "2px solid var(--green-bg)" }}
                >
                  <div className="p-6">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="flex items-center gap-2" style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)" }}>
                        <Sparkles className="w-4 h-4" style={{ color: "var(--green)" }} />
                        AI Study Session
                      </h3>
                      <span className="duo-badge duo-badge-green">
                        Active
                      </span>
                    </div>

                    {/* Content Simulation */}
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>Topic: Contract Law</p>
                        <div className="duo-progress-track">
                          <div
                            className="duo-progress-fill"
                            style={{ width: "75%", backgroundColor: "var(--green)" }}
                          />
                        </div>
                        <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-muted)" }}>
                          75% mastery
                        </p>
                      </div>

                      <div className="space-y-3 pt-4" style={{ borderTop: "2px solid var(--border)" }}>
                        <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
                          Next Concept:
                        </p>
                        <div
                          className="flex items-start gap-3 p-3"
                          style={{
                            borderRadius: "var(--radius-sm)",
                            backgroundColor: "var(--green-bg)",
                            border: "2px solid var(--green-bg)",
                          }}
                        >
                          <Brain className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--green)" }} />
                          <div>
                            <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
                              Consideration in Contracts
                            </p>
                            <p style={{ fontSize: "13px", fontWeight: 500, marginTop: "4px", color: "var(--text-muted)" }}>
                              Adaptive difficulty based on your level
                            </p>
                          </div>
                        </div>
                      </div>

                      <button
                        className="duo-btn duo-btn-outline w-full"
                        style={{ marginTop: "16px" }}
                      >
                        Continue Session
                      </button>
                    </div>
                  </div>

                  {/* Corner Accent */}
                  <div
                    className="absolute top-0 right-0 w-32 h-32 rounded-bl-full"
                    style={{
                      background: "linear-gradient(to bottom left, var(--green-bg), transparent)",
                    }}
                  />
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof Section */}
      <section className="py-12 md:py-16" style={{ borderBottom: "2px solid var(--border)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p style={{ textAlign: "center", fontSize: "12px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "32px", color: "var(--text-muted)" }}>
            Built with insights from top legal minds
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 md:gap-8">
            <div className="flex flex-col items-center text-center gap-3 p-4">
              <div
                className="p-2.5"
                style={{ borderRadius: "var(--radius-full)", backgroundColor: "var(--blue-bg)" }}
              >
                <GraduationCap className="w-6 h-6" style={{ color: "var(--blue)" }} />
              </div>
              <div>
                <p style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)" }}>Top Law Schools</p>
                <p style={{ fontSize: "15px", fontWeight: 500, marginTop: "4px", lineHeight: 1.6, color: "var(--text-muted)" }}>
                  Developed alongside professors from T14 law schools to ensure academic rigor and exam relevance
                </p>
              </div>
            </div>
            <div className="flex flex-col items-center text-center gap-3 p-4">
              <div
                className="p-2.5"
                style={{ borderRadius: "var(--radius-full)", backgroundColor: "var(--green-bg)" }}
              >
                <Shield className="w-6 h-6" style={{ color: "var(--green)" }} />
              </div>
              <div>
                <p style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)" }}>Practicing Attorneys</p>
                <p style={{ fontSize: "15px", fontWeight: 500, marginTop: "4px", lineHeight: 1.6, color: "var(--text-muted)" }}>
                  Refined by experienced lawyers who know what it takes to succeed in the courtroom and on the bar
                </p>
              </div>
            </div>
            <div className="flex flex-col items-center text-center gap-3 p-4">
              <div
                className="p-2.5"
                style={{ borderRadius: "var(--radius-full)", backgroundColor: "var(--gold-bg)" }}
              >
                <Award className="w-6 h-6" style={{ color: "var(--gold)" }} />
              </div>
              <div>
                <p style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)" }}>Bar Examiners</p>
                <p style={{ fontSize: "15px", fontWeight: 500, marginTop: "4px", lineHeight: 1.6, color: "var(--text-muted)" }}>
                  Informed by bar exam graders who understand exactly what earns points and what doesn't
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section
        className="py-16 md:py-24"
        style={{ backgroundColor: "var(--surface-bg)" }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 md:mb-16">
            <h2 style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 900, marginBottom: "16px", letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
              Everything You Need to Ace Your Exams
            </h2>
            <p style={{ fontSize: "18px", fontWeight: 500, maxWidth: "640px", margin: "0 auto", color: "var(--text-muted)" }}>
              Designed specifically for law students who want to study smarter,
              not harder.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <Card padding="lg" className="overflow-hidden">
              <div
                className="mb-4 inline-block p-3"
                style={{ borderRadius: "var(--radius-sm)", backgroundColor: "var(--blue-bg)" }}
              >
                <Brain className="w-6 h-6" style={{ color: "var(--blue)" }} />
              </div>
              <h3 style={{ fontSize: "20px", fontWeight: 800, marginBottom: "12px", color: "var(--text-primary)" }}>
                AI-Powered Tutoring
              </h3>
              <p style={{ fontSize: "15px", fontWeight: 500, lineHeight: 1.6, color: "var(--text-muted)" }}>
                Get personalized lessons from AI that adapts to your knowledge
                level. Choose between OpenAI GPT or Claude for your study
                sessions.
              </p>
            </Card>

            {/* Feature 2 */}
            <Card padding="lg" className="overflow-hidden">
              <div
                className="mb-4 inline-block p-3"
                style={{ borderRadius: "var(--radius-sm)", backgroundColor: "var(--orange-bg)" }}
              >
                <Target className="w-6 h-6" style={{ color: "var(--orange)" }} />
              </div>
              <h3 style={{ fontSize: "20px", fontWeight: 800, marginBottom: "12px", color: "var(--text-primary)" }}>
                Exam-Focused Learning
              </h3>
              <p style={{ fontSize: "15px", fontWeight: 500, lineHeight: 1.6, color: "var(--text-muted)" }}>
                Every concept is tied back to how it appears on exams. Master
                IRAC methodology and spot exam traps before they spot you.
              </p>
            </Card>

            {/* Feature 3 */}
            <Card padding="lg" className="overflow-hidden">
              <div
                className="mb-4 inline-block p-3"
                style={{ borderRadius: "var(--radius-sm)", backgroundColor: "var(--green-bg)" }}
              >
                <Upload className="w-6 h-6" style={{ color: "var(--green)" }} />
              </div>
              <h3 style={{ fontSize: "20px", fontWeight: 800, marginBottom: "12px", color: "var(--text-primary)" }}>
                Smart Document Analysis
              </h3>
              <p style={{ fontSize: "15px", fontWeight: 500, lineHeight: 1.6, color: "var(--text-muted)" }}>
                Upload PDFs, PowerPoints, and readings. The AI extracts key
                concepts and uses them to create focused study sessions.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 md:py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 style={{ fontSize: "clamp(28px, 4vw, 40px)", fontWeight: 900, marginBottom: "24px", letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
            Ready to Transform Your Studies?
          </h2>
          <p style={{ fontSize: "18px", fontWeight: 500, marginBottom: "32px", color: "var(--text-muted)" }}>
            Join law students who are mastering their courses with AI-powered
            study techniques.
          </p>
          <button
            onClick={handleGetStarted}
            className="duo-btn duo-btn-green mx-auto"
            style={{ padding: "12px 24px", fontSize: "18px", display: "inline-flex", alignItems: "center", gap: "8px" }}
          >
            Start Your Free Trial
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: "2px solid var(--border)",
          padding: "32px 0",
          backgroundColor: "var(--surface-bg)",
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center" style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-muted)" }}>
            <p>
              LawFlow - AI Study Companion{" "}
              <span className="mx-2">•</span>
              {new Date().getFullYear()} All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
