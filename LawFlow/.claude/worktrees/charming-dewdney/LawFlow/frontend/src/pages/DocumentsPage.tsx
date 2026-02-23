import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone, FileRejection } from "react-dropzone";
import { listDocuments, uploadDocument, deleteDocument } from "@/api/documents";
import { convertDocument, downloadConvertedFile } from "@/api/converter";
import { formatDate } from "@/lib/utils";
import { SUBJECTS_WITH_AUTODETECT, DOC_TYPES } from "@/lib/constants";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { Upload, FileText, Trash2, Loader2, CheckCircle, AlertCircle, Download } from "lucide-react";

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [subject, setSubject] = useState("");
  const [docType, setDocType] = useState("");
  const [convertingDoc, setConvertingDoc] = useState<string | null>(null);
  const [showConvertMenu, setShowConvertMenu] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

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
      <PageHeader icon={<FileText size={24} />} title="Documents" />

      {/* Upload zone */}
      <Card padding="lg" className="mt-6 mb-6">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="duo-label" style={{ marginBottom: "4px", display: "block" }}>
              Subject
            </label>
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="duo-input w-full"
              aria-label="Subject"
            >
              {SUBJECTS_WITH_AUTODETECT.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="duo-label" style={{ marginBottom: "4px", display: "block" }}>
              Document Type
            </label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="duo-input w-full"
              aria-label="Document Type"
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
            borderColor: isDragActive ? "var(--blue)" : "var(--border)",
            backgroundColor: isDragActive ? "var(--blue-bg)" : "transparent",
          }}
        >
          <input {...getInputProps()} />
          <Upload size={32} className="mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
          <p style={{ color: "var(--text-secondary)", fontWeight: 600 }}>
            {isDragActive
              ? "Drop files here..."
              : "Drag & drop PDF, PPTX, or DOCX files here"}
          </p>
          <p style={{ fontSize: "12px", marginTop: "4px", color: "var(--text-muted)" }}>
            Or click to browse. Max 100MB.
          </p>
        </div>
      </Card>

      {/* Document list */}
      {isLoading ? (
        <div style={{ color: "var(--text-muted)" }}>Loading documents...</div>
      ) : docs.length === 0 ? (
        <EmptyState
          icon={<FileText size={40} />}
          message="No documents uploaded yet"
          sub="Upload your first casebook, slides, or outline above."
        />
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <Card key={doc.id} padding="none" className="px-4 py-3 flex items-center gap-4">
              <FileText size={20} className="shrink-0" style={{ color: "var(--text-muted)" }} />
              <div className="flex-1 min-w-0">
                <p className="truncate" style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
                  {doc.filename}
                </p>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  {doc.subject || "untagged"} · {doc.file_type} · {formatDate(doc.created_at)}
                </p>
              </div>
              <StatusBadge
                status={doc.processing_status}
                chunks={doc.total_chunks}
                errorMessage={doc.error_message}
              />
              
              {doc.file_type === "pptx" && (
                <div className="relative" ref={showConvertMenu === doc.id ? menuRef : null}>
                  <button
                    onClick={() => setShowConvertMenu(showConvertMenu === doc.id ? null : doc.id)}
                    disabled={convertingDoc === doc.id}
                    className="p-1.5 transition-colors rounded"
                    style={{ color: "var(--blue-dark)" }}
                    title="Convert to another format"
                  >
                    {convertingDoc === doc.id ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Download size={16} />
                    )}
                  </button>
                  
                  {showConvertMenu === doc.id && (
                    <Card
                      padding="none"
                      className="absolute right-0 mt-1 py-1 shadow-lg z-10"
                      style={{ minWidth: "160px" }}
                    >
                      <button
                        onClick={() => handleConvert(doc.id, "pdf")}
                        className="w-full text-left px-3 py-2 transition-colors"
                        style={{ fontSize: "14px", color: "var(--text-primary)" }}
                      >
                        Convert to PDF
                      </button>
                      <button
                        onClick={() => handleConvert(doc.id, "png")}
                        className="w-full text-left px-3 py-2 transition-colors"
                        style={{ fontSize: "14px", color: "var(--text-primary)" }}
                      >
                        Convert to Images
                      </button>
                      <button
                        onClick={() => handleConvert(doc.id, "txt")}
                        className="w-full text-left px-3 py-2 transition-colors"
                        style={{ fontSize: "14px", color: "var(--text-primary)" }}
                      >
                        Convert to Text
                      </button>
                      <button
                        onClick={() => handleConvert(doc.id, "md")}
                        className="w-full text-left px-3 py-2 transition-colors"
                        style={{ fontSize: "14px", color: "var(--text-primary)" }}
                      >
                        Convert to Markdown
                      </button>
                    </Card>
                  )}
                </div>
              )}
              
              <button
                onClick={() => deleteMutation.mutate(doc.id)}
                className="p-1 transition-colors"
                style={{ color: "var(--text-muted)" }}
                title="Delete document"
              >
                <Trash2 size={16} />
              </button>
            </Card>
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
        <Badge variant="green" className="flex items-center gap-1.5">
          <CheckCircle size={12} />
          {chunks} chunks
        </Badge>
      );
    case "processing":
      return (
        <Badge variant="blue" className="flex items-center gap-1.5">
          <Loader2 size={12} className="animate-spin" />
          Processing
        </Badge>
      );
    case "error":
      return (
        <Badge variant="red" className="flex items-center gap-1.5 max-w-xs" title={errorMessage || "Processing failed"}>
          <AlertCircle size={12} className="shrink-0" />
          <span className="truncate">{errorMessage || "Error"}</span>
        </Badge>
      );
    default:
      return (
        <Badge>Pending</Badge>
      );
  }
}
