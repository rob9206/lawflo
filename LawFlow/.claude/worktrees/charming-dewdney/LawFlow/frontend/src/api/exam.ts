import api from "@/lib/api";

export interface ExamQuestion {
  id: string;
  assessment_id: string;
  question_index: number;
  question_type: "mc" | "essay" | "issue_spot";
  question_text: string;
  options: string[] | null;
  correct_answer: string | null;
  student_answer: string | null;
  is_correct: boolean | null;
  score: number | null;
  feedback: string | null;
  grading?: IracGrading | IssueSpotGrading | null;
  subject: string;
  topic: string;
  difficulty: number;
}

export interface IracGrading {
  issue_spotting: number;
  rule_accuracy: number;
  application_depth: number;
  conclusion_support: number;
  overall_score: number;
  issues_found?: string[];
  issues_missed?: string[];
  strengths?: string;
  weaknesses?: string;
  feedback: string;
}

export interface IssueSpotGrading {
  issues_found: string[];
  issues_missed: string[];
  false_positives?: string[];
  score: number;
  feedback: string;
}

export interface ExamAssessment {
  id: string;
  assessment_type: string;
  subject: string;
  topics: string[];
  total_questions: number;
  score: number | null;
  time_limit_minutes: number | null;
  time_taken_minutes: number | null;
  is_timed: boolean;
  feedback_summary: string | null;
  created_at: string;
  completed_at: string | null;
  questions?: ExamQuestion[];
  topic_breakdown?: Record<string, number>;
  irac_breakdown?: {
    issue_spotting: number | null;
    rule_accuracy: number | null;
    application_depth: number | null;
    conclusion_support: number | null;
  };
}

export async function generateExam(
  subject: string,
  format: string = "mixed",
  numQuestions: number = 5,
  timeMinutes: number = 60
): Promise<ExamAssessment> {
  const { data } = await api.post("/exam/generate", {
    subject,
    format,
    num_questions: numQuestions,
    time_minutes: timeMinutes,
  });
  return data;
}

export async function submitAnswer(
  questionId: string,
  answer: string
): Promise<ExamQuestion> {
  const { data } = await api.post("/exam/answer", {
    question_id: questionId,
    answer,
  });
  return data;
}

export async function completeExam(
  assessmentId: string
): Promise<ExamAssessment> {
  const { data } = await api.post(`/exam/complete/${assessmentId}`);
  return data;
}

export async function getExamResults(
  assessmentId: string
): Promise<ExamAssessment> {
  const { data } = await api.get(`/exam/results/${assessmentId}`);
  return data;
}

export async function getExamHistory(
  subject?: string,
  limit = 10
): Promise<ExamAssessment[]> {
  const { data } = await api.get("/exam/history", {
    params: { subject: subject || undefined, limit },
  });
  return data;
}
