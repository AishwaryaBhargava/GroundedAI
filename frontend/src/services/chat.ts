import { apiFetch } from "./api";

export type QueryRequest = {
  workspace_id: string;
  query: string;
  top_k?: number;
  document_id?: string | null;
  include_answer?: boolean;
};

export type RetrievalChunk = {
  document_id: string;
  chunk_index: number;
  page_start: number;
  page_end: number;
  token_count: number;
  score: number;
  content: string;
};

export type QueryResponse = {
  workspace_id: string;
  query: string;
  top_k: number;
  results: RetrievalChunk[];
  answer: string | null;
  citations: ChatCitation[] | null;
  refused: boolean | null;
  refusal_reason: string | null;
};

export type ChatCitation = {
  document_id: string;
  chunk_index: number;
  page_start: number;
  page_end: number;
  snippet: string;
};

export type AnswerResponse = {
  workspace_id: string;
  query: string;
  answer: string | null;
  citations: ChatCitation[];
  refused: boolean;
  refusal_reason: string | null;
};

export type ChatHistoryMessage = {
  id: string;
  query: string;
  answer: string | null;
  citations: ChatCitation[] | null;
  refused: boolean;
  refusal_reason: string | null;
  created_at: string;
};

export type ChatHistoryResponse = {
  document_id: string;
  messages: ChatHistoryMessage[];
};

export async function queryWorkspace(payload: QueryRequest): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      document_id: payload.document_id || null,
    }),
  });
}

export async function answerQuery(payload: QueryRequest): Promise<AnswerResponse> {
  return apiFetch<AnswerResponse>("/answer", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      document_id: payload.document_id || null,
    }),
  });
}

export async function getDocumentChatHistory(
  documentId: string
): Promise<ChatHistoryResponse> {
  return apiFetch<ChatHistoryResponse>(`/documents/${documentId}/chat`, {
    method: "GET",
  });
}
