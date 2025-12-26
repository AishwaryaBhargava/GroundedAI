import { API_BASE, getSessionId, apiFetch } from "./api";

export type DocumentItem = {
  id: string;
  filename: string;
  status: string;
  file_type: string;
  file_size: number;
  created_at: string;
};

export type UploadResponse = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
};

export type ChunkPreview = {
  chunk_index: number;
  page_start: number | null;
  page_end: number | null;
  token_count: number;
  content_preview: string;
};

export type DocumentSummaryNotStarted = {
  document_id: string;
  status: "not_started";
};

export type DocumentSummaryRunning = {
  document_id: string;
  status: "running";
};

export type DocumentSummaryCompleted = {
  document_id: string;
  status: "completed";
  bullet_points: string[];
  narrative_summary: string;
  suggested_questions: string[];
  model: string | null;
  token_usage: Record<string, unknown> | null;
  updated_at: string;
};

export type DocumentSummaryFailed = {
  document_id: string;
  status: "failed";
  error_reason?: string | null;
};

export type DocumentSummaryResponse =
  | DocumentSummaryNotStarted
  | DocumentSummaryRunning
  | DocumentSummaryCompleted
  | DocumentSummaryFailed;

export async function listDocuments(workspaceId: string): Promise<DocumentItem[]> {
  const encoded = encodeURIComponent(workspaceId);
  return apiFetch<DocumentItem[]>(`/documents?workspace_id=${encoded}`, { method: "GET" });
}

export async function uploadDocument(
  workspaceId: string,
  file: File
): Promise<UploadResponse> {
  const sessionId = getSessionId();
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(
    `${API_BASE}/documents/upload?workspace_id=${encodeURIComponent(workspaceId)}`,
    {
      method: "POST",
      headers: {
        ...(sessionId ? { "x-guest-session": sessionId } : {}),
      },
      body: form,
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Upload failed: ${res.status}`);
  }

  return res.json() as Promise<UploadResponse>;
}

export async function embedDocument(documentId: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/documents/${documentId}/embed`, {
    method: "POST",
  });
}

export async function getDocumentFileUrl(
  documentId: string
): Promise<{ url: string; expires_in: number }> {
  return apiFetch<{ url: string; expires_in: number }>(
    `/documents/${documentId}/file-url`,
    { method: "GET" }
  );
}

export async function listChunks(documentId: string): Promise<ChunkPreview[]> {
  return apiFetch<ChunkPreview[]>(`/documents/${documentId}/chunks`, { method: "GET" });
}

export async function getDocumentSummary(
  documentId: string
): Promise<DocumentSummaryResponse> {
  return apiFetch<DocumentSummaryResponse>(`/documents/${documentId}/summary`, {
    method: "GET",
  });
}

export async function generateDocumentSummary(
  documentId: string
): Promise<DocumentSummaryResponse> {
  return apiFetch<DocumentSummaryResponse>(`/documents/${documentId}/summary`, {
    method: "POST",
  });
}
