import api from "@/lib/api";
import type { Document } from "@/types";

export async function uploadDocument(
  file: File,
  subject?: string,
  docType?: string
): Promise<{ id: string; status: string; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);
  if (subject) formData.append("subject", subject);
  if (docType) formData.append("doc_type", docType);

  const { data } = await api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listDocuments(params?: {
  subject?: string;
  status?: string;
}): Promise<Document[]> {
  const { data } = await api.get("/documents", { params });
  return data;
}

export async function getDocument(id: string): Promise<Document> {
  const { data } = await api.get(`/documents/${id}`);
  return data;
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`);
}
