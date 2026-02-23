import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { KnowledgeChunk } from "@/types";
import { Search, FileText, Tag } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";

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
      <PageHeader title="Knowledge Base" />

      <div className="flex gap-3 mb-6 mt-6">
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
            className="duo-input w-full pl-9 pr-3 py-2"
            style={{ fontSize: 14 }}
          />
        </div>
        <select
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          aria-label="Filter by subject"
          className="duo-input px-3 py-2"
          style={{ fontSize: 14 }}
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
          aria-label="Filter by content type"
          className="duo-input px-3 py-2"
          style={{ fontSize: 14 }}
        >
          <option value="">All types</option>
          <option value="rule">Rules</option>
          <option value="case">Cases</option>
          <option value="concept">Concepts</option>
          <option value="procedure">Procedures</option>
          <option value="definition">Definitions</option>
        </select>
      </div>

      {isLoading ? (
        <div style={{ fontSize: 14, fontWeight: 500, color: "var(--text-muted)" }}>Searching...</div>
      ) : chunks.length === 0 ? (
        <EmptyState
          icon={<FileText size={40} />}
          message="No knowledge chunks found."
          sub="Upload documents to build your knowledge base."
        />
      ) : (
        <div className="space-y-3">
          {chunks.map((chunk) => (
            <Card key={chunk.id}>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="blue">{chunk.subject}</Badge>
                {chunk.topic && <Badge>{chunk.topic}</Badge>}
                <Badge>{chunk.content_type}</Badge>
                {chunk.case_name && (
                  <Badge variant="orange" className="flex items-center gap-1">
                    <Tag size={10} />
                    {chunk.case_name}
                  </Badge>
                )}
              </div>
              {chunk.summary && (
                <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 8, color: "var(--text-secondary)" }}>
                  {chunk.summary}
                </p>
              )}
              <p className="line-clamp-3" style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>
                {chunk.content}
              </p>
              {chunk.key_terms.length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap">
                  {chunk.key_terms.map((term) => (
                    <Badge key={term} className="text-[10px]">
                      {term}
                    </Badge>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
