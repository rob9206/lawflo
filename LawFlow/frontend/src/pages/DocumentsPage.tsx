import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone, FileRejection } from "react-dropzone";
import { listDocuments, uploadDocument, deleteDocument } from "@/api/documents";
import { formatDate } from "@/lib/utils";
import { Upload, FileText, Trash2, Loader2, CheckCircle, AlertCircle } from "lucide-react";

const SUBJECTS = [
  { value: "", label: "Auto-detect" },
  { value: "con_law", label: "Constitutional Law" },
  { value: "contracts", label: "Contracts" },
  { value: "torts", label: "Torts" },
  { value: "crim_law", label: "Criminal Law" },
  { value: "civ_pro", label: "Civil Procedure" },
  { value: "property", label: "Property" },
  { value: "evidence", label: "Evidence" },
  { value: "prof_responsibility", label: "Professional Responsibility" },
];

const DOC_TYPES = [
  { value: "", label: "Auto-detect" },
  { value: "casebook", label: "Casebook / Textbook" },
  { value: "slides", label: "Lecture Slides" },
  { value: "outline", label: "Outline / Notes" },
  { value: "exam", label: "Past Exam" },
  { value: "supplement", label: "Supplement" },
];

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [subject, setSubject] = useState("");
  const [docType, setDocType] = useState("");

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => listDocuments(),
    refetchInterval: 5000, // Poll for processing status
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      uploadDocument(file, subject || undefined, docType || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      // Handle accepted files
      for (const file of acceptedFiles) {
        uploadMutation.mutate(file);
      }
      
      // Handle rejected files - check if they're valid by extension (MIME type might be wrong)
      for (const rejection of fileRejections) {
        if (rejection.errors.some(e => e.code === 'file-invalid-type')) {
          const ext = rejection.file.name.split('.').pop()?.toLowerCase();
          if (ext === 'pptx' || ext === 'pdf' || ext === 'docx') {
            // File extension is valid, accept it anyway despite MIME type mismatch
            uploadMutation.mutate(rejection.file);
          }
        }
      }
    },
    [uploadMutation, subject, docType]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "application/vnd.ms-powerpoint": [".pptx"],
      "application/octet-stream": [".pptx"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".docx"],
    },
    maxSize: 100 * 1024 * 1024,
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Documents</h2>

      {/* Upload zone */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Subject</label>
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {SUBJECTS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Document Type</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {DOC_TYPES.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? "border-indigo-500 bg-indigo-500/10"
              : "border-zinc-700 hover:border-zinc-600"
          }`}
        >
          <input {...getInputProps()} />
          <Upload size={32} className="mx-auto mb-3 text-zinc-500" />
          <p className="text-zinc-300">
            {isDragActive
              ? "Drop files here..."
              : "Drag & drop PDF, PPTX, or DOCX files here"}
          </p>
          <p className="text-xs text-zinc-500 mt-1">Or click to browse. Max 100MB.</p>
        </div>
      </div>

      {/* Document list */}
      {isLoading ? (
        <div className="text-zinc-500">Loading documents...</div>
      ) : docs.length === 0 ? (
        <div className="text-zinc-500 text-center py-8">
          No documents uploaded yet. Upload your first casebook, slides, or outline above.
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <div
              key={doc.id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 flex items-center gap-4"
            >
              <FileText size={20} className="text-zinc-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.filename}</p>
                <p className="text-xs text-zinc-500">
                  {doc.subject || "untagged"} · {doc.file_type} · {formatDate(doc.created_at)}
                </p>
              </div>
              <StatusBadge status={doc.processing_status} chunks={doc.total_chunks} errorMessage={doc.error_message} />
              <button
                onClick={() => deleteMutation.mutate(doc.id)}
                className="p-1 text-zinc-500 hover:text-red-400 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status, chunks, errorMessage }: { status: string; chunks: number; errorMessage?: string | null }) {
  switch (status) {
    case "completed":
      return (
        <span className="flex items-center gap-1.5 text-xs text-green-400 bg-green-500/10 px-2.5 py-1 rounded-full">
          <CheckCircle size={12} />
          {chunks} chunks
        </span>
      );
    case "processing":
      return (
        <span className="flex items-center gap-1.5 text-xs text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full">
          <Loader2 size={12} className="animate-spin" />
          Processing
        </span>
      );
    case "error":
      return (
        <span
          className="flex items-center gap-1.5 text-xs text-red-400 bg-red-500/10 px-2.5 py-1 rounded-full max-w-xs"
          title={errorMessage || "Processing failed"}
        >
          <AlertCircle size={12} className="shrink-0" />
          <span className="truncate">{errorMessage || "Error"}</span>
        </span>
      );
    default:
      return (
        <span className="text-xs text-zinc-500 px-2.5 py-1">Pending</span>
      );
  }
}
