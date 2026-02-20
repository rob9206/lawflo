import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { KnowledgeChunk } from "@/types";
import { Search, FileText, Tag } from "lucide-react";

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [subject, setSubject] = useState("");
  const [contentType, setContentType] = useState("");

  const { data: chunks = [], isLoading } = useQuery({
    queryKey: ["knowledge", query, subject, contentType],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (query) params.q = query;
      if (subject) params.subject = subject;
      if (contentType) params.content_type = contentType;
      const { data } = await api.get<KnowledgeChunk[]>("/knowledge/search", { params });
      return data;
    },
  });

  const { data: subjects = [] } = useQuery({
    queryKey: ["knowledge-subjects"],
    queryFn: async () => {
      const { data } = await api.get("/knowledge/subjects");
      return data as { subject: string; chunk_count: number }[];
    },
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6" style={{ color: "var(--text-primary)" }}>
        Knowledge Base
      </h2>

      {/* Search / filter bar */}
      <div className="flex gap-3 mb-6">
        <div className="flex-1 relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: "var(--text-muted)" }}
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search knowledge chunks..."
            className="w-full rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2"
            style={{
              backgroundColor: "var(--bg-input)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          />
        </div>
        <select
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="rounded-lg px-3 py-2 text-sm focus:outline-none"
          style={{
            backgroundColor: "var(--bg-input)",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
          }}
        >
          <option value="">All subjects</option>
          {subjects.map((s) => (
            <option key={s.subject} value={s.subject}>
              {s.subject} ({s.chunk_count})
            </option>
          ))}
        </select>
        <select
          value={contentType}
          onChange={(e) => setContentType(e.target.value)}
          className="rounded-lg px-3 py-2 text-sm focus:outline-none"
          style={{
            backgroundColor: "var(--bg-input)",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
          }}
        >
          <option value="">All types</option>
          <option value="rule">Rules</option>
          <option value="case">Cases</option>
          <option value="concept">Concepts</option>
          <option value="procedure">Procedures</option>
          <option value="definition">Definitions</option>
        </select>
      </div>

      {/* Results */}
      {isLoading ? (
        <div style={{ color: "var(--text-muted)" }}>Searching...</div>
      ) : chunks.length === 0 ? (
        <div className="text-center py-12">
          <FileText size={40} className="mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
          <p style={{ color: "var(--text-muted)" }}>No knowledge chunks found.</p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Upload documents to build your knowledge base.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {chunks.map((chunk) => (
            <div
              key={chunk.id}
              className="rounded-xl p-4"
              style={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-card)",
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: "var(--accent-muted)",
                    color: "var(--accent-text)",
                  }}
                >
                  {chunk.subject}
                </span>
                {chunk.topic && (
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-secondary)" }}
                  >
                    {chunk.topic}
                  </span>
                )}
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-muted)" }}
                >
                  {chunk.content_type}
                </span>
                {chunk.case_name && (
                  <span className="text-xs flex items-center gap-1 text-amber-400">
                    <Tag size={10} />
                    {chunk.case_name}
                  </span>
                )}
              </div>
              {chunk.summary && (
                <p className="text-sm mb-2" style={{ color: "var(--text-secondary)" }}>
                  {chunk.summary}
                </p>
              )}
              <p className="text-xs line-clamp-3" style={{ color: "var(--text-muted)" }}>
                {chunk.content}
              </p>
              {chunk.key_terms.length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap">
                  {chunk.key_terms.map((term) => (
                    <span
                      key={term}
                      className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: "var(--bg-muted)", color: "var(--text-muted)" }}
                    >
                      {term}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
