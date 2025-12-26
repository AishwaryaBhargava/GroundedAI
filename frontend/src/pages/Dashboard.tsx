import { useEffect, useState } from "react";
import "../styles/Dashboard.css";
import Sidebar from "../components/dashboard/Sidebar";
import WorkspaceMain from "../components/dashboard/WorkspaceMain";
import ChatPanel from "../components/dashboard/ChatPanel";
import {
  embedDocument,
  generateDocumentSummary,
  getDocumentSummary,
  listDocuments,
  uploadDocument,
} from "../services/documents";
import type { DocumentItem } from "../services/documents";
import type { ChatCitation } from "../services/chat";

export default function Dashboard() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<ChatCitation | null>(null);

  const getErrorMessage = (error: any, fallback: string) => {
    const message = error?.message || fallback;
    if (typeof message !== "string") return fallback;
    try {
      const parsed = JSON.parse(message);
      return parsed?.detail || message;
    } catch {
      return message;
    }
  };

  const refreshDocuments = async (targetWorkspaceId?: string | null) => {
    const id = targetWorkspaceId ?? workspaceId;
    if (!id) {
      setDocuments([]);
      setSelectedDocumentId(null);
      return;
    }

    setDocumentsLoading(true);
    try {
      const docs = await listDocuments(id);
      setDocuments(docs);
      if (!selectedDocumentId || !docs.find((d) => d.id === selectedDocumentId)) {
        setSelectedDocumentId(docs[0]?.id || null);
      }
    } finally {
      setDocumentsLoading(false);
    }
  };

  useEffect(() => {
    refreshDocuments(workspaceId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  useEffect(() => {
    if (!activeCitation) return;
    if (activeCitation.document_id !== selectedDocumentId) {
      setActiveCitation(null);
    }
  }, [activeCitation, selectedDocumentId]);

  const handleUpload = async (file: File) => {
    if (!workspaceId) return;
    setUploading(true);
    setUploadError(null);
    setProcessingStatus("Uploading document...");
    try {
      const uploaded = await uploadDocument(workspaceId, file);
      setSelectedDocumentId(uploaded.id);
      setProcessingStatus("Processing document...");
      await embedDocument(uploaded.id);
      setProcessingStatus("Finalizing summary...");
      try {
        const summary = await getDocumentSummary(uploaded.id);
        if (summary.status === "not_started") {
          await generateDocumentSummary(uploaded.id);
        }
      } catch (summaryError: any) {
        setUploadError(getErrorMessage(summaryError, "Summary generation failed"));
      }
      await refreshDocuments(workspaceId);
    } catch (e: any) {
      setUploadError(getErrorMessage(e, "Upload failed"));
    } finally {
      setUploading(false);
      setProcessingStatus(null);
    }
  };

  return (
    <div className="dashboard">
      <aside className="dashboard-sidebar">
        <Sidebar
          selectedWorkspaceId={workspaceId}
          onSelectWorkspace={setWorkspaceId}
          documents={documents}
          documentsLoading={documentsLoading}
          selectedDocumentId={selectedDocumentId}
          onSelectDocument={setSelectedDocumentId}
          onUploadDocument={handleUpload}
          uploading={uploading}
          uploadError={uploadError}
          showUploadInSidebar={Boolean(selectedDocumentId)}
          uploadDisabled={!workspaceId || documents.length >= 10 || uploading}
          disableWorkspaceCreate={uploading}
          docLimitReached={documents.length >= 10}
        />
      </aside>

      <section className="dashboard-main">
        <WorkspaceMain
          workspaceId={workspaceId}
          documents={documents}
          selectedDocumentId={selectedDocumentId}
          onUploadDocument={handleUpload}
          uploading={uploading}
          uploadError={uploadError}
          processingStatus={processingStatus}
          uploadDisabled={!workspaceId || documents.length >= 10 || uploading}
          showUpload={!selectedDocumentId}
          activeCitation={activeCitation}
        />
      </section>

      <aside className="dashboard-right">
        <ChatPanel
          workspaceId={workspaceId}
          selectedDocumentId={selectedDocumentId}
          selectedCitation={activeCitation}
          onSelectCitation={setActiveCitation}
        />
      </aside>
    </div>
  );
}
