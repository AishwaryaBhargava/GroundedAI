import { useEffect, useId, useMemo, useRef, useState } from "react";
import "../../styles/WorkspaceMain.css";
import {
  getDocumentFileUrl,
  listChunks,
} from "../../services/documents";
import type { DocumentItem } from "../../services/documents";
import type { ChatCitation } from "../../services/chat";
import {
  GlobalWorkerOptions,
  getDocument,
  type PDFDocumentProxy,
} from "pdfjs-dist";
import type { TextItem } from "pdfjs-dist/types/src/display/api";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min?url";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "text/csv",
];
const ACCEPTED_LABELS = ["PDF", "DOCX", "PPTX", "TXT", "CSV"];
const MAX_FILE_MB = 10;

type Props = {
  workspaceId: string | null;
  documents: DocumentItem[];
  selectedDocumentId: string | null;
  onUploadDocument: (file: File) => void;
  uploading: boolean;
  uploadError: string | null;
  processingStatus: string | null;
  uploadDisabled: boolean;
  showUpload: boolean;
  activeCitation: ChatCitation | null;
};

export default function WorkspaceMain({
  workspaceId,
  documents,
  selectedDocumentId,
  onUploadDocument,
  uploading,
  uploadError,
  processingStatus,
  uploadDisabled,
  showUpload,
  activeCitation,
}: Props) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState<string | null>(null);
  const [previewRows, setPreviewRows] = useState<string[][] | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [pdfPageNumber, setPdfPageNumber] = useState(1);
  const [pdfPageLoading, setPdfPageLoading] = useState(false);
  const [pdfZoom, setPdfZoom] = useState(1.35);
  const [pdfHighlights, setPdfHighlights] = useState<
    { top: number; left: number; width: number; height: number }[]
  >([]);
  const pdfCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const pdfHighlightLayerRef = useRef<HTMLDivElement | null>(null);
  const pdfContainerRef = useRef<HTMLDivElement | null>(null);
  const uploadInputId = useId();

  const selectedDocument = useMemo(
    () => documents.find((d) => d.id === selectedDocumentId) || null,
    [documents, selectedDocumentId]
  );

  useEffect(() => {
    GlobalWorkerOptions.workerSrc = pdfjsWorker;
  }, []);

  const activeCitationForDoc = useMemo(() => {
    if (!selectedDocument || !activeCitation) return null;
    if (activeCitation.document_id !== selectedDocument.id) return null;
    return activeCitation;
  }, [activeCitation, selectedDocument]);

  const formatPages = (start?: number, end?: number) => {
    if (typeof start !== "number" && typeof end !== "number") return null;
    const safeStart = typeof start === "number" ? start : end;
    const safeEnd = typeof end === "number" ? end : start;
    if (safeStart === safeEnd) return `Page ${safeStart}`;
    return `Pages ${safeStart}-${safeEnd}`;
  };

  const renderPreviewText = () => {
    const text = previewText || "No preview available.";
    const snippet = activeCitationForDoc?.snippet;
    if (!snippet) return text;

    const normalizeWithMap = (value: string) => {
      const normalizedChars: string[] = [];
      const indexMap: number[] = [];
      let lastWasSpace = false;

      for (let i = 0; i < value.length; i += 1) {
        const char = value[i];
        const isSpace = /\s/.test(char);
        if (isSpace) {
          if (lastWasSpace) continue;
          normalizedChars.push(" ");
          indexMap.push(i);
          lastWasSpace = true;
        } else {
          normalizedChars.push(char.toLowerCase());
          indexMap.push(i);
          lastWasSpace = false;
        }
      }

      return {
        normalized: normalizedChars.join("").trim(),
        indexMap,
      };
    };

    const { normalized: normalizedText, indexMap } = normalizeWithMap(text);
    const { normalized: normalizedSnippet } = normalizeWithMap(snippet);

    if (!normalizedSnippet) return text;

    const normalizedIndex = normalizedText.indexOf(normalizedSnippet);
    if (normalizedIndex === -1) return text;

    const startIndex = indexMap[normalizedIndex];
    const endIndex = indexMap[normalizedIndex + normalizedSnippet.length - 1] + 1;

    return (
      <>
        {text.slice(0, startIndex)}
        <mark className="preview-highlight">{text.slice(startIndex, endIndex)}</mark>
        {text.slice(endIndex)}
      </>
    );
  };

  const normalizeForMatch = (value: string) =>
    value
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();

  const buildPdfHighlights = (
    items: TextItem[],
    snippet: string | undefined,
    viewport: { convertToViewportRectangle: (rect: number[]) => number[] }
  ) => {
    if (!snippet) return [];
    const normalizedSnippet = normalizeForMatch(snippet);
    if (!normalizedSnippet) return [];

    let combined = "";
    const charToItem: number[] = [];
    items.forEach((item, itemIndex) => {
      const normalizedItem = normalizeForMatch(item.str);
      if (!normalizedItem) return;
      if (combined.length > 0) {
        combined += " ";
        charToItem.push(-1);
      }
      for (let i = 0; i < normalizedItem.length; i += 1) {
        combined += normalizedItem[i];
        charToItem.push(itemIndex);
      }
    });

    const findMatchIndex = (needle: string) => combined.indexOf(needle);
    let matchIndex = findMatchIndex(normalizedSnippet);
    if (matchIndex === -1) {
      const words = normalizedSnippet.split(" ").filter(Boolean);
      const shorter = words.slice(0, 8).join(" ");
      if (shorter) {
        matchIndex = findMatchIndex(shorter);
      }
    }
    if (matchIndex === -1) return [];

    const matchEnd = Math.min(
      matchIndex + normalizedSnippet.length - 1,
      combined.length - 1
    );
    const matchedItems = new Set<number>();
    for (let i = matchIndex; i <= matchEnd; i += 1) {
      const itemIndex = charToItem[i];
      if (itemIndex >= 0) matchedItems.add(itemIndex);
    }

    const highlights: { top: number; left: number; width: number; height: number }[] = [];
    matchedItems.forEach((itemIndex) => {
      const item = items[itemIndex];
      const x = item.transform[4];
      const y = item.transform[5];
      const width = item.width;
      const height = item.height;
      const [x1, y1, x2, y2] = viewport.convertToViewportRectangle([
        x,
        y,
        x + width,
        y + height,
      ]);
      const left = Math.min(x1, x2);
      const top = Math.min(y1, y2);
      const rectWidth = Math.abs(x2 - x1);
      const rectHeight = Math.abs(y2 - y1);
      highlights.push({ top, left, width: rectWidth, height: rectHeight });
    });

    return highlights;
  };

  useEffect(() => {
    if (!pdfDoc) return;
    const targetPage = activeCitationForDoc?.page_start || activeCitationForDoc?.page_end;
    if (!targetPage) return;
    setPdfPageNumber(
      Math.min(Math.max(targetPage, 1), pdfDoc.numPages)
    );
  }, [activeCitationForDoc, pdfDoc]);

  useEffect(() => {
    if (!pdfDoc) return;
    let canceled = false;
    const renderPage = async () => {
      setPdfPageLoading(true);
      try {
        const page = await pdfDoc.getPage(pdfPageNumber);
        if (canceled) return;
        const baseViewport = page.getViewport({ scale: 1 });
        const containerWidth = pdfContainerRef.current?.clientWidth || baseViewport.width;
        const fitScale = containerWidth / baseViewport.width;
        const zoomScale = Math.min(Math.max(pdfZoom, 0.75), 2.5);
        const dpr = window.devicePixelRatio || 1;
        const renderViewport = page.getViewport({ scale: fitScale * zoomScale * dpr });
        const viewport = page.getViewport({ scale: fitScale * zoomScale });
        const canvas = pdfCanvasRef.current;
        const highlightLayer = pdfHighlightLayerRef.current;
        if (!canvas || !highlightLayer) return;
        const context = canvas.getContext("2d");
        if (!context) return;

        canvas.width = renderViewport.width;
        canvas.height = renderViewport.height;
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;
        highlightLayer.style.width = `${viewport.width}px`;
        highlightLayer.style.height = `${viewport.height}px`;

        await page.render({ canvasContext: context, viewport: renderViewport }).promise;
        const textContent = await page.getTextContent();
        if (canceled) return;
        const highlights = buildPdfHighlights(
          textContent.items as TextItem[],
          activeCitationForDoc?.snippet,
          viewport
        );
        setPdfHighlights(highlights);
      } catch {
        if (!canceled) {
          setPdfHighlights([]);
        }
      } finally {
        if (!canceled) {
          setPdfPageLoading(false);
        }
      }
    };

    renderPage();
    return () => {
      canceled = true;
    };
  }, [activeCitationForDoc, pdfDoc, pdfPageNumber, pdfZoom]);

  useEffect(() => {
    const loadPreview = async () => {
      const parseCsv = (csvText: string) => {
        const rows: string[][] = [];
        let row: string[] = [];
        let current = "";
        let inQuotes = false;

        for (let i = 0; i < csvText.length; i += 1) {
          const char = csvText[i];
          const next = csvText[i + 1];

          if (char === '"') {
            if (inQuotes && next === '"') {
              current += '"';
              i += 1;
            } else {
              inQuotes = !inQuotes;
            }
          } else if (char === "," && !inQuotes) {
            row.push(current);
            current = "";
          } else if ((char === "\n" || char === "\r") && !inQuotes) {
            if (char === "\r" && next === "\n") {
              i += 1;
            }
            row.push(current);
            current = "";
            if (row.length > 1 || row[0]?.trim()) {
              rows.push(row);
            }
            row = [];
          } else {
            current += char;
          }
        }

        row.push(current);
        if (row.length > 1 || row[0]?.trim()) {
          rows.push(row);
        }

        return rows;
      };

      if (!selectedDocument) {
        setPreviewUrl(null);
        setPreviewText(null);
        setPreviewRows(null);
        setPreviewError(null);
        setPdfDoc(null);
        setPdfPageNumber(1);
        setPdfHighlights([]);
        return;
      }

      setLoadingPreview(true);
      setPreviewError(null);
      setPreviewText(null);
      setPreviewRows(null);
      setPdfDoc(null);
      setPdfHighlights([]);
      try {
        const { url } = await getDocumentFileUrl(selectedDocument.id);
        setPreviewUrl(url);

        if (selectedDocument.file_type === "application/pdf") {
          const loadingTask = getDocument(url);
          const pdf = await loadingTask.promise;
          setPdfDoc(pdf);
          setPdfPageNumber(1);
          setPdfZoom(1.35);
          return;
        }

        if (
          selectedDocument.file_type === "text/plain" ||
          selectedDocument.file_type === "text/csv"
        ) {
          try {
            const res = await fetch(url);
            if (!res.ok) {
              throw new Error(`Failed to load file: ${res.status}`);
            }
            const text = await res.text();
            if (selectedDocument.file_type === "text/csv") {
              const rows = parseCsv(text);
              setPreviewRows(rows.length ? rows : null);
              setPreviewText(null);
            } else {
              setPreviewText(text || "No preview available.");
            }
          } catch {
            const chunks = await listChunks(selectedDocument.id);
            const fallback = chunks[0]?.content_preview || "No preview available.";
            if (selectedDocument.file_type === "text/csv") {
              const rows = parseCsv(fallback);
              setPreviewRows(rows.length ? rows : null);
              setPreviewText(null);
            } else {
              setPreviewText(fallback);
            }
          }
        }
      } catch (e: any) {
        setPreviewError(e.message || "Failed to load preview");
      } finally {
        setLoadingPreview(false);
      }
    };

    loadPreview();
  }, [selectedDocument]);

  const acceptAttr = ACCEPTED_TYPES.join(",");

  return (
    <section className="workspace-main">
      <h2>Documents</h2>

      {showUpload && (
        <div className="upload-placeholder">
          <label className="upload-icon-label" htmlFor={uploadInputId}>
            <span className="upload-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img" aria-label="">
                <path
                  d="M12 16V6m0 0l-4 4m4-4l4 4M5 18h14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          </label>
          <label
            className={`upload-action ${uploadDisabled ? "upload-action--disabled" : ""}`}
            htmlFor={uploadInputId}
            aria-disabled={uploadDisabled}
          >
            Click to upload
          </label>
          <p className="upload-hint">
            {ACCEPTED_LABELS.join(", ")} up to {MAX_FILE_MB}MB
          </p>
          <input
            className="upload-input"
            id={uploadInputId}
            type="file"
            accept={acceptAttr}
            disabled={!workspaceId || uploading || uploadDisabled}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                onUploadDocument(file);
                e.currentTarget.value = "";
              }
            }}
          />
          {uploadError && <p className="muted">{uploadError}</p>}
          {uploadDisabled && (
            <p className="muted">Document upload limit reached.</p>
          )}
        </div>
      )}

      <div className="doc-preview">
        {processingStatus && (
          <div className="processing-status">{processingStatus}</div>
        )}
        {activeCitationForDoc &&
          formatPages(activeCitationForDoc.page_start, activeCitationForDoc.page_end) && (
            <div className="preview-source">
              Source: {formatPages(activeCitationForDoc.page_start, activeCitationForDoc.page_end)}
            </div>
          )}
        {!selectedDocument && !processingStatus && (
          <p className="muted">Select a document to preview</p>
        )}
        {selectedDocument && loadingPreview && <p className="muted">Loading preview...</p>}
        {selectedDocument && previewError && <p className="muted">{previewError}</p>}
        {selectedDocument && !loadingPreview && !previewError && (
          <>
            {selectedDocument.file_type === "application/pdf" && (
              <div className="pdf-viewer">
                <div className="pdf-toolbar">
                  <button
                    type="button"
                    className="pdf-nav"
                    onClick={() => setPdfPageNumber((prev) => Math.max(prev - 1, 1))}
                    disabled={!pdfDoc || pdfPageNumber <= 1}
                  >
                    Prev
                  </button>
                  <div className="pdf-zoom">
                    <button
                      type="button"
                      className="pdf-zoom-btn"
                      onClick={() => setPdfZoom((prev) => Math.max(prev - 0.1, 0.75))}
                      aria-label="Zoom out"
                    >
                      -
                    </button>
                    <span className="pdf-zoom-label">
                      {Math.round(Math.min(Math.max(pdfZoom, 0.75), 2.5) * 100)}%
                    </span>
                    <button
                      type="button"
                      className="pdf-zoom-btn"
                      onClick={() => setPdfZoom((prev) => Math.min(prev + 0.1, 2.5))}
                      aria-label="Zoom in"
                    >
                      +
                    </button>
                  </div>
                  <span className="pdf-page">
                    Page {pdfPageNumber}
                    {pdfDoc ? ` of ${pdfDoc.numPages}` : ""}
                  </span>
                  <button
                    type="button"
                    className="pdf-nav"
                    onClick={() =>
                      setPdfPageNumber((prev) =>
                        pdfDoc ? Math.min(prev + 1, pdfDoc.numPages) : prev
                      )
                    }
                    disabled={!pdfDoc || pdfDoc.numPages <= 1 || pdfPageNumber >= pdfDoc.numPages}
                  >
                    Next
                  </button>
                </div>
                {pdfPageLoading && <p className="muted">Loading page...</p>}
                <div className="pdf-canvas-wrap" ref={pdfContainerRef}>
                  <canvas ref={pdfCanvasRef} className="pdf-canvas" />
                  <div ref={pdfHighlightLayerRef} className="pdf-highlight-layer">
                    {pdfHighlights.map((highlight, index) => (
                      <span
                        key={`pdf-highlight-${index}`}
                        className="pdf-highlight"
                        style={{
                          top: `${highlight.top}px`,
                          left: `${highlight.left}px`,
                          width: `${highlight.width}px`,
                          height: `${highlight.height}px`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            {(selectedDocument.file_type === "text/plain" ||
              selectedDocument.file_type === "text/csv") && (
              <>
                {selectedDocument.file_type === "text/csv" && previewRows?.length ? (
                  <div className="preview-table-wrap">
                    <table className="preview-table">
                      <thead>
                        <tr>
                          {previewRows[0].map((cell, index) => (
                            <th key={`header-${index}`}>{cell}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewRows.slice(1).map((row, rowIndex) => (
                          <tr key={`row-${rowIndex}`}>
                            {row.map((cell, cellIndex) => (
                              <td
                                key={`cell-${rowIndex}-${cellIndex}`}
                                className={
                                  activeCitationForDoc?.snippet &&
                                  cell.includes(activeCitationForDoc.snippet)
                                    ? "preview-cell-highlight"
                                    : ""
                                }
                              >
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <pre className="preview-text">{renderPreviewText()}</pre>
                )}
              </>
            )}
            {selectedDocument.file_type !== "application/pdf" &&
              selectedDocument.file_type !== "text/plain" &&
              selectedDocument.file_type !== "text/csv" && (
                <div className="preview-unavailable">
                  <p className="preview-title">Preview not available</p>
                  <p className="muted">
                    This file type can&#39;t be previewed yet, but you can still
                    ask questions. Convert it to PDF to preview here, or download
                    it to open locally.
                  </p>
                  {previewUrl && (
                    <a
                      className="download-button"
                      href={previewUrl}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Download file
                    </a>
                  )}
                </div>
              )}
          </>
        )}
      </div>
    </section>
  );
}
