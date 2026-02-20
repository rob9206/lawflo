export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number | null;
  subject: string | null;
  doc_type: string | null;
  processing_status: "pending" | "processing" | "completed" | "error";
  error_message: string | null;
  total_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeChunk {
  id: string;
  document_id: string;
  content: string;
  summary: string | null;
  chunk_index: number;
  subject: string;
  topic: string | null;
  subtopic: string | null;
  difficulty: number;
  content_type: string;
  case_name: string | null;
  key_terms: string[];
  created_at: string;
}

export interface SubjectMastery {
  id: string;
  subject: string;
  display_name: string;
  mastery_score: number;
  total_study_time_minutes: number;
  sessions_count: number;
  assessments_count: number;
  last_studied_at: string | null;
  topic_count?: number;
  topics?: TopicMastery[];
}

export interface TopicMastery {
  id: string;
  subject: string;
  topic: string;
  display_name: string;
  mastery_score: number;
  confidence: number;
  exposure_count: number;
  correct_count: number;
  incorrect_count: number;
  last_tested_at: string | null;
  last_studied_at: string | null;
}

export interface TutorSession {
  id: string;
  session_type: string;
  tutor_mode: string | null;
  subject: string | null;
  topics: string[];
  started_at: string;
  ended_at: string | null;
  duration_minutes: number | null;
  messages_count: number;
  performance_score: number | null;
  messages?: SessionMessage[];
}

export interface SessionMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  message_index: number;
  created_at: string;
}

export interface TutorMode {
  name: string;
  description: string;
}

export interface DashboardData {
  subjects: SubjectMastery[];
  stats: {
    total_subjects: number;
    total_knowledge_chunks: number;
    total_sessions: number;
    total_study_minutes: number;
    overall_mastery: number;
  };
}
