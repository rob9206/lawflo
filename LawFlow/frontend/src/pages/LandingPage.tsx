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

export default function LandingPage() {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "var(--bg-base)", color: "var(--text-primary)" }}>
      {/* Navigation Bar */}
      <nav
        className="sticky top-0 z-50 backdrop-blur-md border-b"
        style={{ 
          backgroundColor: "var(--bg-base)",
          borderColor: "var(--border)"
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-6 h-6" style={{ color: "var(--accent)" }} />
            <span className="text-xl font-bold">LawFlow</span>
          </div>
          <button
            onClick={handleGetStarted}
            className="btn-primary px-4 py-2 text-sm font-semibold"
          >
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="flex-1 min-h-screen flex items-center py-12 md:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            {/* Left Column */}
            <div className="space-y-6 animate-fade-in">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-serif font-bold leading-tight tracking-tight">
                Master Law School. Efficiently.
              </h1>

              <p className="text-lg leading-relaxed max-w-xl text-ui-secondary">
                Stop falling behind. Get AI tutoring that knows exactly where
                you're struggling and drills you on what actually shows up on
                exams.
              </p>

              <button
                onClick={handleGetStarted}
                className="btn-primary group px-6 py-3 text-lg font-semibold"
              >
                Get Started Free
                <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </button>

              {/* Trust Indicators */}
              <div className="space-y-3 pt-4">
                <div className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                  <span className="text-sm font-medium">Free to start</span>
                </div>
                <div className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                  <span className="text-sm font-medium">
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
                  className="absolute inset-0 rounded-2xl blur-3xl"
                  style={{ 
                    background: "linear-gradient(135deg, var(--accent-muted), transparent)"
                  }}
                />

                {/* Mock Study Session Card */}
                <Card
                  padding="none"
                  className="relative border-2 backdrop-blur-sm overflow-hidden shadow-lg"
                  style={{ borderColor: "var(--accent-muted)" }}
                >
                  <div className="p-6">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="font-semibold flex items-center gap-2">
                        <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
                        AI Study Session
                      </h3>
                      <span 
                        className="text-xs px-3 py-1 rounded-full font-medium"
                        style={{ 
                          backgroundColor: "var(--accent-muted)",
                          color: "var(--accent)"
                        }}
                      >
                        Active
                      </span>
                    </div>

                    {/* Content Simulation */}
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <p className="text-sm font-medium">Topic: Contract Law</p>
                        <div 
                          className="h-3 rounded-full overflow-hidden"
                          style={{ backgroundColor: "var(--bg-muted)" }}
                        >
                          <div 
                            className="h-full w-3/4 rounded-full"
                            style={{ backgroundColor: "var(--accent)" }}
                          />
                        </div>
                        <p className="text-xs text-ui-muted">
                          75% mastery
                        </p>
                      </div>

                      <div className="space-y-3 pt-4 border-t" style={{ borderColor: "var(--border)" }}>
                        <p className="text-sm font-medium text-ui-primary">
                          Next Concept:
                        </p>
                        <div 
                          className="flex items-start gap-3 p-3 rounded-lg border"
                          style={{ 
                            backgroundColor: "var(--accent-muted)",
                            borderColor: "var(--accent-muted)"
                          }}
                        >
                          <Brain className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                          <div>
                            <p className="text-sm font-medium">
                              Consideration in Contracts
                            </p>
                            <p className="text-xs mt-1 text-ui-muted">
                              Adaptive difficulty based on your level
                            </p>
                          </div>
                        </div>
                      </div>

                      <button 
                        className="w-full mt-4 py-2 px-4 rounded-lg text-sm font-medium transition-colors"
                        style={{ 
                          backgroundColor: "var(--accent-muted)",
                          color: "var(--accent)"
                        }}
                      >
                        Continue Session
                      </button>
                    </div>
                  </div>

                  {/* Corner Accent */}
                  <div 
                    className="absolute top-0 right-0 w-32 h-32 rounded-bl-full"
                    style={{ 
                      background: "linear-gradient(to bottom left, var(--accent-muted), transparent)"
                    }}
                  />
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof Section */}
      <section className="py-12 md:py-16 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p 
            className="text-center text-sm mb-8 uppercase tracking-widest font-medium text-ui-muted"
          >
            Built with insights from top legal minds
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 md:gap-8">
            <div className="flex flex-col items-center text-center gap-3 p-4">
              <div 
                className="p-2.5 rounded-full"
                style={{ backgroundColor: "var(--accent-muted)" }}
              >
                <GraduationCap className="w-6 h-6" style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <p className="font-semibold text-base">Top Law Schools</p>
                <p className="text-sm mt-1 leading-relaxed text-ui-muted">
                  Developed alongside professors from T14 law schools to ensure academic rigor and exam relevance
                </p>
              </div>
            </div>
            <div className="flex flex-col items-center text-center gap-3 p-4">
              <div 
                className="p-2.5 rounded-full"
                style={{ backgroundColor: "var(--accent-muted)" }}
              >
                <Shield className="w-6 h-6" style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <p className="font-semibold text-base">Practicing Attorneys</p>
                <p className="text-sm mt-1 leading-relaxed text-ui-muted">
                  Refined by experienced lawyers who know what it takes to succeed in the courtroom and on the bar
                </p>
              </div>
            </div>
            <div className="flex flex-col items-center text-center gap-3 p-4">
              <div 
                className="p-2.5 rounded-full"
                style={{ backgroundColor: "var(--accent-muted)" }}
              >
                <Award className="w-6 h-6" style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <p className="font-semibold text-base">Bar Examiners</p>
                <p className="text-sm mt-1 leading-relaxed text-ui-muted">
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
        style={{ backgroundColor: "var(--bg-muted)" }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 md:mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight">
              Everything You Need to Ace Your Exams
            </h2>
            <p className="text-lg max-w-2xl mx-auto text-ui-muted">
              Designed specifically for law students who want to study smarter,
              not harder.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <Card padding="lg" className="overflow-hidden">
              <div className="mb-4 inline-block p-3 rounded-lg bg-accent-muted">
                <Brain className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-xl font-bold mb-3">AI-Powered Tutoring</h3>
              <p className="leading-relaxed text-ui-muted">
                Get personalized lessons from AI that adapts to your knowledge
                level. Choose between OpenAI GPT or Claude for your study
                sessions.
              </p>
            </Card>

            {/* Feature 2 */}
            <Card padding="lg" className="overflow-hidden">
              <div className="mb-4 inline-block p-3 rounded-lg bg-accent-muted">
                <Target className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-xl font-bold mb-3">Exam-Focused Learning</h3>
              <p className="leading-relaxed text-ui-muted">
                Every concept is tied back to how it appears on exams. Master
                IRAC methodology and spot exam traps before they spot you.
              </p>
            </Card>

            {/* Feature 3 */}
            <Card padding="lg" className="overflow-hidden">
              <div className="mb-4 inline-block p-3 rounded-lg bg-accent-muted">
                <Upload className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-xl font-bold mb-3">
                Smart Document Analysis
              </h3>
              <p className="leading-relaxed text-ui-muted">
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
          <h2 className="text-3xl md:text-4xl font-bold mb-6 tracking-tight">
            Ready to Transform Your Studies?
          </h2>
          <p className="text-lg mb-8 text-ui-muted">
            Join law students who are mastering their courses with AI-powered
            study techniques.
          </p>
          <button
            onClick={handleGetStarted}
            className="btn-primary mx-auto px-6 py-3 text-lg font-semibold"
          >
            Start Your Free Trial
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer 
        className="border-t py-8"
        style={{ 
          borderColor: "var(--border)",
          backgroundColor: "var(--bg-muted)"
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-ui-muted">
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