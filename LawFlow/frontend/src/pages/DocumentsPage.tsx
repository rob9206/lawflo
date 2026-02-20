import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone, FileRejection } from "react-dropzone";
import { listDocuments, uploadDocument, deleteDocument } from "@/api/documents";
import { convertDocument, downloadConvertedFile } from "@/api/converter";
import { formatDate } from "@/lib/utils";
import { Upload, FileText, Trash2, Loader2, CheckCircle, AlertCircle, Download } from "lucide-react";

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
  const [convertingDoc, setConvertingDoc] = useState<string | null>(null);
  const [showConvertMenu, setShowConvertMenu] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowConvertMenu(null);
      }
    };

    if (showConvertMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showConvertMenu]);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => listDocuments(),
    refetchInterval: 5000,
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

  const handleConvert = async (docId: string, format: "pdf" | "png" | "txt" | "md") => {
    setConvertingDoc(docId);
    setShowConvertMenu(null);
    try {
      const result = await convertDocument(docId, format);
      
      if (result.download_url) {
        // Extract filename from download_url
        const filename = result.download_url.split("/").pop();
        if (filename) {
          const downloadUrl = downloadConvertedFile(docId, filename);
          window.open(downloadUrl, "_blank");
        }
      }
      
      alert(result.message);
    } catch (error: any) {
      alert(`Conversion failed: ${error.response?.data?.error || error.message}`);
    } finally {
      setConvertingDoc(null);
    }
  };

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      for (const file of acceptedFiles) {
        uploadMutation.mutate(file);
      }
      for (const rejection of fileRejections) {
        if (rejection.errors.some((e) => e.code === "file-invalid-type")) {
          const ext = rejection.file.name.split(".").pop()?.toLowerCase();
          if (ext === "pptx" || ext === "pdf" || ext === "docx") {
            uploadMutation.mutate(rejection.file);
          }
        }
      }
    },
    [uploadMutation]
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
      <h2 className="text-2xl font-bold mb-6" style={{ color: "var(--text-primary)" }}>
        Documents
      </h2>

      {/* Upload zone */}
      <div
        className="rounded-xl p-6 mb-6"
        style={{
          backgroundColor: "var(--bg-card)",
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-card)",
        }}
      >
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--text-secondary)" }}>
              Subject
            </label>
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
              style={{
                backgroundColor: "var(--bg-muted)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            >
              {SUBJECTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--text-secondary)" }}>
              Document Type
            </label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
              style={{
                backgroundColor: "var(--bg-muted)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            >
              {DOC_TYPES.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div
          {...getRootProps()}
          className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors"
          style={{
            borderColor: isDragActive ? "var(--accent)" : "var(--border)",
            backgroundColor: isDragActive ? "var(--accent-muted)" : "transparent",
          }}
        >
          <input {...getInputProps()} />
          <Upload size={32} className="mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
          <p style={{ color: "var(--text-secondary)" }}>
            {isDragActive
              ? "Drop files here..."
              : "Drag & drop PDF, PPTX, or DOCX files here"}
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Or click to browse. Max 100MB.
          </p>
        </div>
      </div>

      {/* Document list */}
      {isLoading ? (
        <div style={{ color: "var(--text-muted)" }}>Loading documents...</div>
      ) : docs.length === 0 ? (
        <div className="text-center py-8" style={{ color: "var(--text-muted)" }}>
          No documents uploaded yet. Upload your first casebook, slides, or outline above.
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <div
              key={doc.id}
              className="rounded-lg px-4 py-3 flex items-center gap-4"
              style={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--border)",
              }}
            >
              <FileText size={20} className="shrink-0" style={{ color: "var(--text-muted)" }} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                  {doc.filename}
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {doc.subject || "untagged"} · {doc.file_type} · {formatDate(doc.created_at)}
                </p>
              </div>
              <StatusBadge
                status={doc.processing_status}
                chunks={doc.total_chunks}
                errorMessage={doc.error_message}
              />
              
              {/* Convert button for PPTX files */}
              {doc.file_type === "pptx" && (
                <div className="relative">
                  <button
                    onClick={() => setShowConvertMenu(showConvertMenu === doc.id ? null : doc.id)}
                    disabled={convertingDoc === doc.id}
                    className="p-1.5 transition-colors rounded hover:bg-opacity-10"
                    style={{ color: "var(--accent)" }}
                    title="Convert to another format"
                  >
                    {convertingDoc === doc.id ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Download size={16} />
                    )}
                  </button>
                  
                  {showConvertMenu === doc.id && (
                    <div
                      className="absolute right-0 mt-1 py-1 rounded-lg shadow-lg z-10"
                      style={{
                        backgroundColor: "var(--bg-card)",
                        border: "1px solid var(--border)",
                        minWidth: "140px",
                      }}
                    >
                      <button
                        onClick={() => handleConvert(doc.id, "pdf")}
                        className="w-full text-left px-3 py-1.5 text-sm hover:bg-opacity-10 transition-colors"
                        style={{ color: "var(--text-primary)" }}
                      >
                        Convert to PDF
                      </button>
                      <button
                        onClick={() => handleConvert(doc.id, "png")}
                        className="w-full text-left px-3 py-1.5 text-sm hover:bg-opacity-10 transition-colors"
                        style={{ color: "var(--text-primary)" }}
                      >
                        Convert to Images
                      </button>
                      <button
                        onClick={() => handleConvert(doc.id, "txt")}
                        className="w-full text-left px-3 py-1.5 text-sm hover:bg-opacity-10 transition-colors"
                        style={{ color: "var(--text-primary)" }}
                      >
                        Convert to Text
                      </button>
                      <button
                        onClick={() => handleConvert(doc.id, "md")}
                        className="w-full text-left px-3 py-1.5 text-sm hover:bg-opacity-10 transition-colors"
                        style={{ color: "var(--text-primary)" }}
                      >
                        Convert to Markdown
                      </button>
                    </div>
                  )}
                </div>
              )}
              
              <button
                onClick={() => deleteMutation.mutate(doc.id)}
                className="p-1 transition-colors"
                style={{ color: "var(--text-muted)" }}
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

function StatusBadge({
  status,
  chunks,
  errorMessage,
}: {
  status: string;
  chunks: number;
  errorMessage?: string | null;
}) {
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
      return <span className="text-xs px-2.5 py-1" style={{ color: "var(--text-muted)" }}>Pending</span>;
  }
}
