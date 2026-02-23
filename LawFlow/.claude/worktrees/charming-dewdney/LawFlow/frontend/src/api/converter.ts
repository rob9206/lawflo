import axios from "axios";

const API_BASE = "/api";

export interface ConversionRequest {
  format: "pdf" | "png" | "txt" | "md";
}

export interface ConversionResponse {
  format: string;
  message: string;
  download_url?: string;
  files?: string[];
}

export const convertDocument = async (
  docId: string,
  format: "pdf" | "png" | "txt" | "md"
): Promise<ConversionResponse> => {
  const response = await axios.post<ConversionResponse>(
    `${API_BASE}/documents/${docId}/convert`,
    { format }
  );
  return response.data;
};

export const downloadConvertedFile = (docId: string, filename: string): string => {
  return `${API_BASE}/documents/${docId}/download/${filename}`;
};
