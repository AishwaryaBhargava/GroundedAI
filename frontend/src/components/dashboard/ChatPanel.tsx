import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "../../styles/ChatPanel.css";
import {
  generateDocumentSummary,
  getDocumentSummary,
  type DocumentSummaryResponse,
} from "../../services/documents";
import {
  answerQuery,
  getDocumentChatHistory,
  type ChatCitation,
  type ChatHistoryMessage,
} from "../../services/chat";
import logo from "../../assets/logo.svg";

type Props = {
  workspaceId: string | null;
  selectedDocumentId: string | null;
  selectedCitation?: ChatCitation | null;
  onSelectCitation?: (citation: ChatCitation | null) => void;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: ChatCitation[];
  pending?: boolean;
};

export default function ChatPanel({
  workspaceId,
  selectedDocumentId,
  selectedCitation,
  onSelectCitation,
}: Props) {
  const [activeTab, setActiveTab] = useState<"chat" | "summary">("chat");
  const [summary, setSummary] = useState<DocumentSummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const canChat = Boolean(workspaceId && selectedDocumentId);
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

  const buildChatMessages = useCallback(
    (history: ChatHistoryMessage[]): ChatMessage[] => {
      const next: ChatMessage[] = [];
      history.forEach((entry) => {
        next.push({
          id: `${entry.id}-question`,
          role: "user",
          text: entry.query,
        });

        const assistantText =
          entry.refused && entry.refusal_reason
            ? entry.refusal_reason
            : entry.answer || "No answer available.";

        next.push({
          id: `${entry.id}-answer`,
          role: "assistant",
          text: assistantText,
          citations: entry.citations || [],
        });
      });

      return next;
    },
    []
  );

  useEffect(() => {
    if (activeTab !== "summary") return;
    if (!selectedDocumentId) {
      setSummary(null);
      setSummaryError(null);
      return;
    }

    let canceled = false;
    const loadSummary = async () => {
      setSummaryLoading(true);
      setSummaryError(null);
      try {
        const data = await getDocumentSummary(selectedDocumentId);
        if (!canceled) {
          setSummary(data);
        }
      } catch (e: any) {
        if (!canceled) {
          setSummaryError(getErrorMessage(e, "Failed to load summary"));
        }
      } finally {
        if (!canceled) {
          setSummaryLoading(false);
        }
      }
    };

    loadSummary();
    return () => {
      canceled = true;
    };
  }, [activeTab, selectedDocumentId]);

  useEffect(() => {
    if (activeTab !== "chat") return;
    if (!selectedDocumentId) {
      setChatMessages([]);
      setChatError(null);
      return;
    }

    let canceled = false;
    const loadChat = async () => {
      setChatLoading(true);
      setChatError(null);
      try {
        const data = await getDocumentChatHistory(selectedDocumentId);
        if (!canceled) {
          setChatMessages(buildChatMessages(data.messages));
        }
      } catch (e: any) {
        if (!canceled) {
          setChatError(getErrorMessage(e, "Failed to load chat history"));
        }
      } finally {
        if (!canceled) {
          setChatLoading(false);
        }
      }
    };

    loadChat();
    return () => {
      canceled = true;
    };
  }, [activeTab, selectedDocumentId]);

  useEffect(() => {
    if (!chatEndRef.current) return;
    chatEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, activeTab]);

  const handleSend = async () => {
    if (!canChat || chatLoading) return;
    const trimmed = chatInput.trim();
    if (!trimmed) return;

    const pendingId = `pending-${Date.now()}`;
    setChatInput("");
    setChatError(null);
    setChatMessages((prev) => [
      ...prev,
      {
        id: `${pendingId}-question`,
        role: "user",
        text: trimmed,
      },
      {
        id: pendingId,
        role: "assistant",
        text: "Thinking...",
        pending: true,
      },
    ]);

    setChatLoading(true);
    try {
      await answerQuery({
        workspace_id: workspaceId as string,
        document_id: selectedDocumentId as string,
        query: trimmed,
      });
      const history = await getDocumentChatHistory(selectedDocumentId as string);
      setChatMessages(buildChatMessages(history.messages));
    } catch (e: any) {
      setChatMessages((prev) =>
        prev.map((msg) =>
          msg.id === pendingId
            ? {
                ...msg,
                text: getErrorMessage(e, "Failed to send message"),
                pending: false,
              }
            : msg
        )
      );
      setChatError(getErrorMessage(e, "Failed to send message"));
    } finally {
      setChatLoading(false);
    }
  };

  const chatBody = useMemo(() => {
    const truncateSnippet = (text: string, max = 50) => {
      if (text.length <= max) return text;
      return `${text.slice(0, max).trimEnd()}...`;
    };

    const formatPages = (start: number, end: number) => {
      if (!Number.isFinite(start) && !Number.isFinite(end)) return null;
      const safeStart = Number.isFinite(start) ? start : end;
      const safeEnd = Number.isFinite(end) ? end : start;
      if (safeStart === safeEnd) return `Page ${safeStart}`;
      return `Pages ${safeStart}-${safeEnd}`;
    };

    if (!selectedDocumentId) {
      return (
        <div className="chat-empty">
          Select a document to start asking questions.
        </div>
      );
    }

    if (chatLoading && chatMessages.length === 0) {
      return <div className="chat-empty">Loading chat history...</div>;
    }

    if (chatError && chatMessages.length === 0) {
      return <div className="chat-empty">{chatError}</div>;
    }

    if (!chatMessages.length) {
      return (
        <div className="chat-empty">
          {canChat
            ? "Ask your first question about this document."
            : "Ask questions after uploading and processing a document."}
        </div>
      );
    }

    return (
      <div className="chat-messages">
        {chatMessages.map((message) => (
          <div key={message.id} className={`chat-message ${message.role}`}>
            {message.role === "assistant" && (
              <div className="chat-avatar">
                <img src={logo} alt="GroundedAI" />
              </div>
            )}
            <div className="chat-bubble">
              <p>{message.text}</p>
              {message.citations && message.citations.length > 0 && (
                <div className="chat-citations">
                  <h4>Sources</h4>
                  <ul>
                    {message.citations.map((citation, index) => (
                      <li key={`${citation.document_id}-${index}`}>
                        <button
                          type="button"
                          className={`citation-button ${selectedCitation &&
                            selectedCitation.document_id === citation.document_id &&
                            selectedCitation.chunk_index === citation.chunk_index
                            ? "active"
                            : ""
                          }`}
                          title={citation.snippet}
                          onClick={() => {
                            if (!onSelectCitation) return;
                            const isActive =
                              selectedCitation &&
                              selectedCitation.document_id === citation.document_id &&
                              selectedCitation.chunk_index === citation.chunk_index;
                            onSelectCitation(isActive ? null : citation);
                          }}
                        >
                          <span className="citation-snippet">
                            {truncateSnippet(citation.snippet)}
                          </span>
                          {formatPages(citation.page_start, citation.page_end) && (
                            <span className="citation-pages">
                              {formatPages(citation.page_start, citation.page_end)}
                            </span>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
    );
  }, [
    chatError,
    chatLoading,
    chatMessages,
    onSelectCitation,
    selectedCitation,
    selectedDocumentId,
  ]);

  return (
    <div className="chat-panel">
      {/* Tabs */}
      <div className="chat-tabs">
        <button
          className={activeTab === "chat" ? "active" : ""}
          onClick={() => setActiveTab("chat")}
        >
          Chat
        </button>
        <button
          className={activeTab === "summary" ? "active" : ""}
          onClick={() => setActiveTab("summary")}
        >
          Summary
        </button>
      </div>

      {/* Content */}
      <div
        className={`chat-content ${activeTab === "summary" ? "summary-content" : "chat-mode"}`}
      >
        {activeTab === "chat" ? (
          <>
            {chatBody}
            <form
              className="chat-input"
              onSubmit={(event) => {
                event.preventDefault();
                handleSend();
              }}
            >
              <input
                type="text"
                placeholder={
                  canChat ? "Ask a question about this document..." : "Select a document to chat"
                }
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                disabled={!canChat || chatLoading}
              />
              <button type="submit" disabled={!canChat || chatLoading || !chatInput.trim()}>
                Send
              </button>
            </form>
          </>
        ) : (
          <>
            {!selectedDocumentId && (
              <div className="summary-empty">
                Select a document to view its summary.
              </div>
            )}
            {selectedDocumentId && summaryLoading && (
              <div className="summary-empty">Loading summary...</div>
            )}
            {selectedDocumentId && summaryError && (
              <div className="summary-empty">{summaryError}</div>
            )}
            {selectedDocumentId && !summaryLoading && !summaryError && (
              <>
                {summary?.status === "not_started" && (
                  <div className="summary-empty">
                    <p>No summary yet. Click generate to create one.</p>
                    <button
                      type="button"
                      className="download-button"
                      onClick={async () => {
                        if (!selectedDocumentId) return;
                        setSummaryLoading(true);
                        setSummaryError(null);
                        try {
                          const data = await generateDocumentSummary(selectedDocumentId);
                          setSummary(data);
                        } catch (e: any) {
                          setSummaryError(
                            getErrorMessage(e, "Summary generation failed")
                          );
                        } finally {
                          setSummaryLoading(false);
                        }
                      }}
                    >
                      Generate summary
                    </button>
                  </div>
                )}
                {summary?.status === "running" && (
                  <div className="summary-empty">Summary is generating...</div>
                )}
                {summary?.status === "failed" && (
                  <div className="summary-empty">
                    <p>
                      Summary generation failed. Try Again.{" "}
                      {/* {summary.error_reason ? summary.error_reason : ""} */}
                    </p>
                    <button
                      type="button"
                      className="download-button"
                      onClick={async () => {
                        if (!selectedDocumentId) return;
                        setSummaryLoading(true);
                        setSummaryError(null);
                        try {
                          const data = await generateDocumentSummary(selectedDocumentId);
                          setSummary(data);
                        } catch (e: any) {
                          setSummaryError(
                            getErrorMessage(e, "Summary generation failed")
                          );
                        } finally {
                          setSummaryLoading(false);
                        }
                      }}
                    >
                      Generate summary
                    </button>
                  </div>
                )}
                {summary?.status === "completed" && (
                  <div className="summary-body">
                    <div className="summary-section">
                      {/* <h4>Summary</h4> */}
                      <p>{summary.narrative_summary}</p>
                    </div>
                    {summary.bullet_points.length > 0 && (
                      <div className="summary-section">
                        <h4>Key points</h4>
                        <ul>
                          {summary.bullet_points.map((point, index) => (
                            <li key={`${point}-${index}`}>{point}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {summary.suggested_questions.length > 0 && (
                      <div className="summary-section">
                        <h4>Suggested questions</h4>
                        <ul>
                          {summary.suggested_questions.map((question, index) => (
                            <li key={`${question}-${index}`}>{question}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
