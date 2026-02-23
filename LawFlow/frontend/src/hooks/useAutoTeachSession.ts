import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { SessionMessage, TutorSession } from "@/types";
import type {
  AutoTeachLesson,
  CaseExample,
  ExamTrap,
  PracticeQuestion,
  RecognitionPattern,
  Requirement,
} from "@/types/auto-teach";
import { SUBJECT_LABELS } from "@/lib/constants";
import { parseContent } from "@/lib/parseContent";

export interface AutoTeachAPIResponse {
  lesson: AutoTeachLesson;
  session_id: string;
  topic: string;
}

const MODE_LEVELS: Record<string, string> = {
  explain: "Foundational",
  socratic: "Intermediate",
  hypo: "Applied",
  issue_spot: "Exam",
  irac: "Exam",
  exam_strategy: "Exam",
};

function toTitleCase(input: string): string {
  return input
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function humanizeTopic(topic: string): string {
  return toTitleCase(topic.replace(/_/g, " "));
}

function pickLatestAssistantMessage(messages?: SessionMessage[]): string {
  if (!messages?.length) return "";
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].role === "assistant" && messages[i].content) {
      return messages[i].content;
    }
  }
  return "";
}

// ---------------------------------------------------------------------------
// Extraction helpers — return real data or undefined
// ---------------------------------------------------------------------------

function extractRequirements(content: string): Requirement[] {
  const numberedLines = [...content.matchAll(/^\d+\.\s+(.+)$/gm)];
  const reqs = numberedLines
    .map((m) => {
      const rawLine = (m[1] || "").replace(/\*\*/g, "").trim();
      if (!rawLine) return null;

      const split = rawLine.split(/\s*[:\-]\s*/);
      if (split.length >= 2) {
        const [label, ...detailParts] = split;
        return {
          label: label.trim(),
          detail: detailParts.join(" - ").trim() || "Review this rule and apply it to facts.",
        };
      }

      return {
        label: rawLine,
        detail: "Know this requirement and apply it to the facts.",
      };
    })
    .filter((r): r is Requirement => Boolean(r));

  if (reqs.length > 0) return reqs.slice(0, 6);

  const firstParagraph = content.split("\n\n").find((p) => p.trim().length > 20)?.trim();
  return [
    {
      label: "Core Rule",
      detail: firstParagraph || "Study the core rule and be ready to apply it under exam pressure.",
    },
  ];
}

function extractDefinition(content: string): string {
  const chunks = content
    .split(/\n\s*\n/g)
    .map((c) => c.trim())
    .filter(Boolean);

  if (!chunks.length) return "";

  const stopChunk = /^(Key Cases?|Memory Device|Exam Trap|Exam Alert|If you see)/i;
  const selected: string[] = [];

  for (const chunk of chunks) {
    if (stopChunk.test(chunk) && selected.length > 0) {
      break;
    }
    selected.push(chunk);
    if (selected.join("\n\n").length > 900) break;
  }

  return selected.join("\n\n");
}

function extractMnemonic(title: string, content: string): { acronym: string; expansion: string } {
  const explicit = content.match(/Memory Device:\s*"?([A-Za-z0-9\- ]+)"?/i);
  if (explicit?.[1]) {
    const acronym = explicit[1].trim();
    return {
      acronym,
      expansion: `Use ${acronym} to recall the key elements quickly.`,
    };
  }

  const acronym = title
    .split(" ")
    .filter(Boolean)
    .slice(0, 4)
    .map((w) => w.charAt(0).toUpperCase())
    .join("");

  return {
    acronym: acronym || "RULE",
    expansion: "Recall the rule, then apply each element to the facts.",
  };
}

/**
 * Try to find a real case citation in the AI text.
 * Looks for patterns like "Case v. Case (year)" or "In re Case".
 */
function extractCaseExample(content: string): CaseExample | undefined {
  const caseMatch = content.match(
    /(?:Key Case|Case Example|Leading Case)[:\s]*\n?\s*([A-Z][A-Za-z'.]+\s+v\.?\s+[A-Za-z'.]+(?:\s*\([^)]+\))?)/i
  );
  if (!caseMatch?.[1]) return undefined;

  const caseName = caseMatch[1].trim();
  const caseIdx = content.indexOf(caseName);
  const afterCase = content.slice(caseIdx + caseName.length, caseIdx + caseName.length + 600);

  const factsMatch = afterCase.match(/(?:Facts?)[:\s]*\n?\s*([^\n]{15,})/i);
  const holdingMatch = afterCase.match(/(?:Holding|Held|Rule)[:\s]*\n?\s*([^\n]{15,})/i);
  const sigMatch = afterCase.match(/(?:Significance|Importance|Takeaway)[:\s]*\n?\s*([^\n]{15,})/i);

  if (!holdingMatch?.[1]) return undefined;

  return {
    name: caseName,
    facts: factsMatch?.[1]?.trim() || "See lesson text for fact pattern.",
    holding: holdingMatch[1].trim(),
    significance: sigMatch?.[1]?.trim(),
  };
}

/**
 * Try to extract exam traps from AI text.
 * Looks for "Exam Trap", "Common Mistake", "Watch Out" patterns.
 */
function extractExamTraps(content: string): ExamTrap[] | undefined {
  const trapSection = content.match(
    /(?:Exam Trap|Common (?:Exam )?Trap|Common Mistake|Watch Out|Pitfall)s?[:\s]*\n([\s\S]{20,}?)(?=\n(?:Memory Device|If you see|Recognition|Practice|$))/i
  );
  if (!trapSection?.[1]) return undefined;

  const lines = trapSection[1]
    .split("\n")
    .map((l) => l.replace(/^[\-*•]\s*/, "").trim())
    .filter((l) => l.length > 10);

  if (lines.length === 0) return undefined;

  const traps: ExamTrap[] = lines.slice(0, 4).map((line) => {
    const split = line.split(/\s*[:\-–]\s*/);
    if (split.length >= 2) {
      return { trap: split[0].trim(), detail: split.slice(1).join(" - ").trim() };
    }
    return { trap: line.slice(0, 40), detail: line };
  });

  return traps.length > 0 ? traps : undefined;
}

/**
 * Try to extract a recognition pattern ("If you see X → do Y").
 */
function extractRecognitionPattern(content: string): RecognitionPattern | undefined {
  const ifYouSee = content.match(
    /If you see[:\s]*\n?\s*"?([^"\n]{10,})"?\s*\n?\s*(?:→|->|then|respond)[:\s]*\n?\s*"?([^"\n]{10,})"?/i
  );
  if (ifYouSee?.[1] && ifYouSee?.[2]) {
    return {
      trigger: ifYouSee[1].trim(),
      response: ifYouSee[2].trim(),
    };
  }

  const recognition = content.match(
    /Recognition Pattern[:\s]*\n?\s*([^\n]{15,})/i
  );
  if (recognition?.[1]) {
    return {
      trigger: recognition[1].trim(),
      response: "Apply the controlling rule element-by-element to the facts.",
    };
  }

  return undefined;
}

// ---------------------------------------------------------------------------
// Practice question generation
// ---------------------------------------------------------------------------

function shuffleChoices(
  raw: { text: string; correct: boolean }[],
  seed: number,
): { choices: { id: string; text: string }[]; correct: string } {
  const ids = ["A", "B", "C", "D"];
  const reordered = raw.map((_, i) => {
    const srcIdx = (i + seed) % raw.length;
    return { ...raw[srcIdx], id: ids[i] };
  });
  return {
    choices: reordered.map(({ id, text }) => ({ id, text })),
    correct: reordered.find((c) => c.correct)?.id || "B",
  };
}

function extractPracticeQuestions(
  title: string,
  content: string,
  requirements: Requirement[],
): PracticeQuestion[] {
  const lines = content.split("\n").map((l) => l.trim()).filter(Boolean);
  const examTrapLine = lines.find((l) => /^(Exam Trap|Exam Alert|Common Exam Trap)/i.test(l));
  const trapDetail = examTrapLine
    ? lines[lines.indexOf(examTrapLine) + 1]?.trim() || ""
    : "";
  const keyRule = requirements.length >= 2 ? requirements[0].label : title;
  const reqLabels = requirements.slice(0, 3).map((r) => r.label);
  const seed = content.length;
  const questions: PracticeQuestion[] = [];

  {
    const correctText = requirements.length >= 2
      ? `State the rule for ${title}, then apply each element (${reqLabels.join(", ")}) to the specific facts.`
      : `State the controlling rule for ${title} and apply it element-by-element to the facts.`;
    const q = shuffleChoices([
      { text: `Skip the rule statement and jump directly to a conclusion about ${title}.`, correct: false },
      { text: correctText, correct: true },
      { text: `Only discuss broad policy goals without referencing the specific legal test for ${title}.`, correct: false },
      { text: `List every fact in the problem without connecting any to the elements of ${title}.`, correct: false },
    ], seed % 4);
    questions.push({
      stem: `On an exam essay covering ${title}, after identifying the issue, what is the strongest approach to earn maximum points?`,
      ...q,
      explanation: `The best exam answers state the governing rule for ${keyRule} first, then systematically apply each required element to the specific facts in the problem.`,
    });
  }

  if (requirements.length >= 2) {
    const correctReq = requirements[0];
    const wrongReqs = requirements.slice(1, 4);
    const wrongTexts = [
      `"${wrongReqs[0]?.label || "Proximate cause"}" — this element is tested most frequently.`,
      `All elements carry equal weight; there is no single most important element.`,
      `The element the professor spent the least time on in class.`,
    ];
    const q = shuffleChoices([
      { text: `"${correctReq.label}" — ${correctReq.detail.slice(0, 80)}.`, correct: true },
      { text: wrongTexts[0], correct: false },
      { text: wrongTexts[1], correct: false },
      { text: wrongTexts[2], correct: false },
    ], (seed + 1) % 4);
    questions.push({
      stem: `Which element of ${title} is typically the threshold issue an examiner expects you to address first?`,
      ...q,
      explanation: `"${correctReq.label}" is the foundational element. ${correctReq.detail.slice(0, 120)}`,
    });
  }

  if (trapDetail) {
    const q = shuffleChoices([
      { text: `Failing to state the rule before applying it.`, correct: false },
      { text: `${trapDetail.charAt(0).toUpperCase()}${trapDetail.slice(1, 100)}.`, correct: true },
      { text: `Writing too much about policy considerations.`, correct: false },
      { text: `Spending too long on the call of the question.`, correct: false },
    ], (seed + 2) % 4);
    questions.push({
      stem: `What is the most common exam trap students fall into when answering a question about ${title}?`,
      ...q,
      explanation: `The key trap for ${title}: ${trapDetail}. Recognising this pattern on exam day prevents losing easy points.`,
    });
  } else {
    const q = shuffleChoices([
      { text: `Reciting the rule without applying it to the specific facts given.`, correct: true },
      { text: `Writing too much factual analysis.`, correct: false },
      { text: `Citing too many cases in support.`, correct: false },
      { text: `Spending time on counter-arguments.`, correct: false },
    ], (seed + 2) % 4);
    questions.push({
      stem: `What is the most common mistake students make when writing about ${title} on an exam?`,
      ...q,
      explanation: `The #1 mistake is "rule dump" — restating doctrine without connecting each element to the facts. Exams reward application, not recitation.`,
    });
  }

  if (requirements.length >= 3) {
    const r1 = requirements[0];
    const r2 = requirements[1];
    const q = shuffleChoices([
      { text: `"${r1.label}" focuses on ${r1.detail.slice(0, 60)}, while "${r2.label}" addresses ${r2.detail.slice(0, 60)}.`, correct: true },
      { text: `They are essentially the same element stated in different words.`, correct: false },
      { text: `"${r2.label}" is a subset of "${r1.label}" and need not be analysed separately.`, correct: false },
      { text: `Courts have merged these two elements into a single test in modern jurisprudence.`, correct: false },
    ], (seed + 3) % 4);
    questions.push({
      stem: `How do you distinguish "${r1.label}" from "${r2.label}" in a ${title} analysis?`,
      ...q,
      explanation: `These are distinct elements. "${r1.label}": ${r1.detail.slice(0, 80)}. "${r2.label}": ${r2.detail.slice(0, 80)}. Treating them separately earns more points.`,
    });
  }

  if (questions.length === 0) {
    const q = shuffleChoices([
      { text: `State the rule, then apply each element to the facts.`, correct: true },
      { text: `Only state the rule without application.`, correct: false },
      { text: `Skip the rule and discuss policy.`, correct: false },
      { text: `List facts without legal analysis.`, correct: false },
    ], seed % 4);
    questions.push({
      stem: `What is the best approach to an exam question on ${title}?`,
      ...q,
      explanation: `Always state the rule first, then apply each element to the specific facts.`,
    });
  }

  return questions;
}

function extractAIPracticeQuestions(rawText: string): PracticeQuestion[] | null {
  const match = rawText.match(/<practice_questions>\s*([\s\S]*?)\s*<\/practice_questions>/);
  if (!match?.[1]) return null;

  try {
    const parsed = JSON.parse(match[1]);
    if (!Array.isArray(parsed) || parsed.length === 0) return null;

    const valid = parsed.filter(
      (q: unknown): q is PracticeQuestion => {
        if (!q || typeof q !== "object") return false;
        const obj = q as Record<string, unknown>;
        return (
          typeof obj.stem === "string" &&
          Array.isArray(obj.choices) &&
          obj.choices.length >= 2 &&
          typeof obj.correct === "string" &&
          typeof obj.explanation === "string"
        );
      }
    );

    return valid.length > 0 ? valid : null;
  } catch {
    return null;
  }
}

function stripMetadataTags(text: string): string {
  return text
    .replace(/<practice_questions>[\s\S]*?<\/practice_questions>/g, "")
    .replace(/<performance>[\s\S]*?<\/performance>/g, "")
    .trim();
}

// ---------------------------------------------------------------------------
// Main builder
// ---------------------------------------------------------------------------

function buildLessonFromSession(session: TutorSession): AutoTeachLesson {
  const topicKey = session.topics?.[0] || "auto_teach_topic";
  const title = humanizeTopic(topicKey);
  const category = SUBJECT_LABELS[session.subject || ""] || "AutoTeach";
  const level = MODE_LEVELS[session.tutor_mode || ""] || "Foundational";
  const assistantRawText = pickLatestAssistantMessage(session.messages);
  const aiQuestions = extractAIPracticeQuestions(assistantRawText);
  const assistantText = parseContent(stripMetadataTags(assistantRawText));

  const firstLine = assistantText.split("\n").find((line) => line.trim().length > 0)?.trim() || "";
  const subtitle = firstLine.startsWith("#")
    ? firstLine.replace(/^#+\s*/, "").replace(/\s+/g, " ").trim()
    : "Auto-generated study session";

  const definition =
    extractDefinition(assistantText) ||
    assistantText ||
    "No assistant lesson text was stored for this session. Return to AutoTeach and start a new lesson.";

  const requirements = extractRequirements(assistantText);
  const mnemonic = extractMnemonic(title, assistantText);

  const caseExample = extractCaseExample(assistantRawText);
  const examTraps = extractExamTraps(assistantRawText);
  const recognitionPattern = extractRecognitionPattern(assistantRawText);

  const practiceQuestions =
    aiQuestions ?? extractPracticeQuestions(title, assistantText, requirements);

  return {
    title,
    subtitle,
    category,
    level,
    topicKey,
    definition,
    mnemonic,
    requirements,
    practiceQuestions,
    ...(caseExample && { caseExample }),
    ...(examTraps && { examTraps }),
    ...(recognitionPattern && { recognitionPattern }),
  };
}

export function useAutoTeachSession(sessionId: string | undefined) {
  return useQuery<AutoTeachAPIResponse>({
    queryKey: ["auto-teach-session", sessionId],
    queryFn: async () => {
      const { data } = await api.get<TutorSession>(`/tutor/session/${sessionId}`);
      const lesson = buildLessonFromSession(data);
      return {
        lesson,
        session_id: data.id,
        topic: lesson.topicKey,
      };
    },
    enabled: Boolean(sessionId),
    staleTime: 5 * 60 * 1000,
  });
}
