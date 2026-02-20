import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import Layout from "@/components/common/Layout";

const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const DocumentsPage = lazy(() => import("@/pages/DocumentsPage"));
const TutorPage = lazy(() => import("@/pages/TutorPage"));
const KnowledgePage = lazy(() => import("@/pages/KnowledgePage"));
const AutoTeachPage = lazy(() => import("@/pages/AutoTeachPage"));
const FlashcardPage = lazy(() => import("@/pages/FlashcardPage"));
const ProgressPage = lazy(() => import("@/pages/ProgressPage"));
const SubjectsListPage = lazy(() =>
  import("@/pages/SubjectsPage").then((m) => ({ default: m.SubjectsListPage }))
);
const SubjectDetailPage = lazy(() =>
  import("@/pages/SubjectsPage").then((m) => ({ default: m.SubjectDetailPage }))
);
const ExamSimulatorPage = lazy(() => import("@/pages/ExamSimulatorPage"));

function Loading() {
  return (
    <div
      className="flex items-center justify-center h-64"
      style={{ color: "var(--text-muted)" }}
    >
      <div className="animate-pulse">Loading...</div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/tutor" element={<TutorPage />} />
            <Route path="/tutor/:sessionId" element={<TutorPage />} />
            <Route path="/auto-teach" element={<AutoTeachPage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/flashcards" element={<FlashcardPage />} />
            <Route path="/progress" element={<ProgressPage />} />
            <Route path="/subjects" element={<SubjectsListPage />} />
            <Route path="/subjects/:subject" element={<SubjectDetailPage />} />
            <Route path="/exam" element={<ExamSimulatorPage />} />
          </Routes>
        </Suspense>
      </Layout>
    </BrowserRouter>
  );
}
