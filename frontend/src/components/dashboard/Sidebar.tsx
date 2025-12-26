import { useEffect, useId, useState } from "react";
import "../../styles/Sidebar.css";
import { createWorkspace, listWorkspaces } from "../../services/workspaces";
import type { Workspace } from "../../services/workspaces";
import type { DocumentItem } from "../../services/documents";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "text/csv",
];

type Props = {
  selectedWorkspaceId?: string | null;
  onSelectWorkspace?: (id: string) => void;
  documents?: DocumentItem[];
  documentsLoading?: boolean;
  selectedDocumentId?: string | null;
  onSelectDocument?: (id: string) => void;
  onUploadDocument?: (file: File) => void;
  uploading?: boolean;
  uploadError?: string | null;
  showUploadInSidebar?: boolean;
  uploadDisabled?: boolean;
  disableWorkspaceCreate?: boolean;
  docLimitReached?: boolean;
};

export default function Sidebar({
  selectedWorkspaceId,
  onSelectWorkspace,
  documents = [],
  documentsLoading = false,
  selectedDocumentId,
  onSelectDocument,
  onUploadDocument,
  uploading = false,
  uploadError = null,
  showUploadInSidebar = false,
  uploadDisabled = false,
  disableWorkspaceCreate = false,
  docLimitReached = false,
}: Props) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [limitReached, setLimitReached] = useState(false);

  const [isCreating, setIsCreating] = useState(false);
  const uploadInputId = useId();
  const acceptAttr = ACCEPTED_TYPES.join(",");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const ws = await listWorkspaces();
      setWorkspaces(ws);
      const isGuest = ws.some((item) => item.is_guest);
      setLimitReached(isGuest && ws.length >= 5);

      if (!selectedWorkspaceId && ws.length && onSelectWorkspace) {
        onSelectWorkspace(ws[0].id);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load workspaces");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate() {
    const name = newName.trim();
    if (!name || limitReached || disableWorkspaceCreate) return;

    setCreating(true);
    setError(null);
    try {
      const created = await createWorkspace(name);
      setWorkspaces((prev) => [created, ...prev]);
      setLimitReached(created.is_guest && workspaces.length + 1 >= 5);
      setNewName("");
      setIsCreating(false);
      if (onSelectWorkspace) onSelectWorkspace(created.id);
    } catch (e: any) {
      const message = e?.message || "Failed to create workspace";
      const parsed = (() => {
        try {
          const json = JSON.parse(message);
          return json?.detail || message;
        } catch {
          return message;
        }
      })();
      if (parsed.toLowerCase().includes("limit reached")) {
        setLimitReached(true);
        setError(null);
        setIsCreating(false);
        return;
      }
      setError(parsed);
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    if (limitReached) {
      setIsCreating(false);
    }
  }, [limitReached]);

  return (
    <aside className="sidebar">
      <h3 className="sidebar-title">Workspace</h3>

      {error && <div className="sidebar-error">{error}</div>}

      {/* CREATE WORKSPACE */}
      <div className="sidebar-create">
        {!isCreating ? (
          <button
            className="sidebar-add"
            onClick={() => setIsCreating(true)}
            disabled={limitReached || disableWorkspaceCreate}
          >
            + Create Workspace
          </button>
        ) : (
          <div className="create-inline">
            <input
              className="sidebar-input"
              placeholder="Workspace name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              autoFocus
              disabled={creating || limitReached || disableWorkspaceCreate}
            />
            <button
              className="create-confirm"
              onClick={handleCreate}
              disabled={
                creating || limitReached || disableWorkspaceCreate || !newName.trim()
              }
              title="Create"
            >
              ➜
            </button>
          </div>
        )}
        {limitReached && (
          <div className="sidebar-limit">Workspace limit reached.</div>
        )}
      </div>

      {loading ? (
        <p className="muted">Loading...</p>
      ) : (
        <div className="workspace-list">
          {workspaces.map((w) => {
            const active = w.id === selectedWorkspaceId;
            return (
              <button
                key={w.id}
                className={`workspace-item ${active ? "active" : ""}`}
                onClick={() => onSelectWorkspace?.(w.id)}
                type="button"
              >
                {w.name}
              </button>
            );
          })}
          {!workspaces.length && <p className="muted">No workspaces yet</p>}
        </div>
      )}

      <div className="sidebar-section">
        <h4>Documents</h4>
        {showUploadInSidebar && onUploadDocument && (
          <div className="sidebar-upload">
            <input
              className="sidebar-upload-input"
              id={uploadInputId}
              type="file"
              accept={acceptAttr}
              disabled={uploadDisabled || uploading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  onUploadDocument(file);
                  e.currentTarget.value = "";
                }
              }}
            />
            <label
              className={`sidebar-add ${uploadDisabled ? "sidebar-add--disabled" : ""}`}
              htmlFor={uploadInputId}
              aria-disabled={uploadDisabled}
            >
              + Upload Document
            </label>
            {uploadError && <p className="muted">{uploadError}</p>}
            {docLimitReached && (
              <div className="sidebar-limit">Document limit reached.</div>
            )}
          </div>
        )}
        {documentsLoading ? (
          <p className="muted">Loading...</p>
        ) : documents.length ? (
          <div className="document-list">
            {documents.map((doc) => {
              const active = doc.id === selectedDocumentId;
              return (
                <button
                  key={doc.id}
                  className={`document-item ${active ? "active" : ""}`}
                  onClick={() => onSelectDocument?.(doc.id)}
                  type="button"
                >
                  <span className="document-name">{doc.filename}</span>
                  {/* <span className="document-meta">{doc.status}</span> */}
                </button>
              );
            })}
          </div>
        ) : (
          <p className="muted">No documents uploaded</p>
        )}
      </div>
    </aside>
  );
}
