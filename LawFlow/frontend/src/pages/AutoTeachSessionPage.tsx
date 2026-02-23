import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import AutoTeachCard from "@/components/auto-teach/AutoTeachCard";
import { useAutoTeachSession } from "@/hooks/useAutoTeachSession";
import type { AutoTeachLesson } from "@/types/auto-teach";

const FALLBACK_LESSON: AutoTeachLesson = {
  title: "Actus Reus",
  subtitle: "The Criminal Act Rule",
  category: "Criminal Law",
  level: "Foundational",
  topicKey: "actus_reus",
  definition:
    "The physical element of a crime. There must be a voluntary act (or omission where duty exists) that causes the prohibited result.",
  mnemonic: {
    acronym: "VAC-S",
    expansion: "Voluntary Act Causes Social harm",
  },
  requirements: [
    {
      label: "Voluntary Act",
      detail:
        "Conscious, willed bodily movement - not reflexive or coerced. The defendant must have exercised control over the physical act.",
    },
    {
      label: "Causation",
      detail: "The act must be the actual and proximate cause of the prohibited harm.",
    },
    {
      label: "Harm",
      detail: "Damage to person, property, or society must result from the act.",
    },
    {
      label: "Concurrence",
      detail: "Act and mens rea must exist simultaneously - the guilty mind must accompany the guilty act.",
    },
  ],
  caseExample: {
    name: "Martin v. State (1944)",
    court: "Alabama Court of Appeals",
    facts:
      "Defendant was arrested at his home while intoxicated. Police officers carried him onto a public highway, where he was charged with being drunk in a public place.",
    holding:
      "No actus reus - the act of appearing drunk in public was involuntary because police physically transported him there.",
    significance: "Establishes that criminal liability requires a voluntary act by the defendant.",
  },
  examTraps: [
    {
      trap: "Thoughts alone",
      detail:
        'Thoughts are never actus reus - a physical act is required. "Thinking about killing someone" does not equal a crime.',
    },
    {
      trap: "Status crimes",
      detail:
        "Being something (addict, vagrant) vs. doing something. Robinson v. California held status crimes unconstitutional.",
    },
    {
      trap: "Possession",
      detail:
        "Must be knowing possession. Distinguish constructive (control over location) from actual (on person).",
    },
  ],
  recognitionPattern: {
    trigger: "Defendant was sleepwalking / having a seizure / physically forced by others",
    response: "Challenge actus reus -> involuntary act defense",
  },
  practiceQuestions: [
    {
      stem: "Police find Marcus passed out drunk in a park. They carry him to the sidewalk outside a bar, where he is arrested for public intoxication. Marcus argues he has an actus reus defense. Which best supports his argument?",
      choices: [
        { id: "A", text: "Being drunk in public is sufficient actus reus regardless of how he arrived there." },
        { id: "B", text: "The act of being on the sidewalk was involuntary because police placed him there, so no actus reus exists." },
        { id: "C", text: "Marcus voluntarily became intoxicated, satisfying the voluntary act requirement." },
        { id: "D", text: "Omissions can never satisfy actus reus, so his failure to leave is not criminal." },
      ],
      correct: "B",
      explanation:
        "Martin v. State (1944) is directly on point. The physical act of appearing in public must itself be voluntary. Police transported Marcus involuntarily.",
    },
    {
      stem: 'Which element of Actus Reus is typically the threshold issue an examiner expects you to address first?',
      choices: [
        { id: "A", text: '"Voluntary Act" — Conscious, willed bodily movement, not reflexive or coerced.' },
        { id: "B", text: '"Causation" — this element is tested most frequently.' },
        { id: "C", text: "All elements carry equal weight; there is no single most important element." },
        { id: "D", text: "The element the professor spent the least time on in class." },
      ],
      correct: "A",
      explanation:
        '"Voluntary Act" is the foundational element. Without a voluntary act, there is no actus reus to analyse further.',
    },
    {
      stem: "What is the most common exam trap students fall into when answering a question about Actus Reus?",
      choices: [
        { id: "A", text: "Reciting the rule without applying it to the specific facts given." },
        { id: "B", text: "Writing too much factual analysis." },
        { id: "C", text: "Citing too many cases in support." },
        { id: "D", text: "Spending time on counter-arguments." },
      ],
      correct: "A",
      explanation:
        'The #1 mistake is "rule dump" — restating doctrine without connecting each element to the facts. Exams reward application, not recitation.',
    },
  ],
};

export default function AutoTeachSessionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { sessionId } = useParams<{ sessionId: string }>();
  const demoMode = searchParams.get("demo") === "1";
  const { data, isLoading, error } = useAutoTeachSession(demoMode ? undefined : sessionId);

  if (demoMode) {
    return <AutoTeachCard lesson={FALLBACK_LESSON} onBack={() => navigate("/auto-teach")} />;
  }

  if (!sessionId) {
    return (
      <div className="p-6">
        <p className="mb-3" style={{ fontSize: 14, fontWeight: 600, color: "var(--red)" }}>
          Invalid session URL. Missing session id.
        </p>
        <button
          type="button"
          onClick={() => navigate("/auto-teach")}
          className="duo-btn duo-btn-outline"
        >
          Back to AutoTeach
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-muted)" }}>Loading session...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="mb-2" style={{ fontSize: 14, fontWeight: 600, color: "var(--red)" }}>
          Could not load this session.
        </p>
        <p className="mb-4" style={{ fontSize: 13, fontWeight: 500, color: "var(--text-muted)" }}>
          {error instanceof Error ? error.message : "The session could not be loaded."}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate("/auto-teach")}
            className="duo-btn duo-btn-outline"
          >
            Back to AutoTeach
          </button>
          <button
            type="button"
            onClick={() => navigate(`/auto-teach/session/${sessionId}?demo=1`)}
            className="duo-btn duo-btn-outline"
          >
            Open Demo Lesson
          </button>
        </div>
      </div>
    );
  }

  if (!data?.lesson) {
    return (
      <div className="p-6">
        <p className="mb-2" style={{ fontSize: 14, fontWeight: 600, color: "var(--red)" }}>
          Session loaded without lesson data.
        </p>
        <p className="mb-4" style={{ fontSize: 13, fontWeight: 500, color: "var(--text-muted)" }}>
          Backend did not return a `lesson` object for this session.
        </p>
        <button
          type="button"
          onClick={() => navigate("/auto-teach")}
          className="duo-btn duo-btn-outline"
        >
          Back to AutoTeach
        </button>
      </div>
    );
  }

  return <AutoTeachCard lesson={data.lesson} onBack={() => navigate("/auto-teach")} />;
}
