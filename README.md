<h1 align="left">
  <img
    src="frontend/public/logo.svg"
    alt="GroundedAI Logo"
    width="40"
    style="vertical-align: middle; margin-right: 10px;"
  />
  GroundedAI
</h1>

<p><strong>Document-grounded Q&A with verifiable citations</strong></p>
<p><strong>Live Website:</strong> <a href="https://grounded-ai.vercel.app">https://grounded-ai.vercel.app/</a></p>

---

## Overview

**GroundedAI** is a document-grounded question-answering web application that allows users to upload their own documents and ask questions that are answered **strictly from the uploaded content**.

Every answer includes **verifiable citations** (document, page/chunk, and source snippet).
If the answer is not supported by the documents, the system **refuses** or asks for clarification.

The core focus of GroundedAI is **trust**:

* No hallucinated answers
* No guessing beyond the documents
* Clear evidence for every response

---

## Problem Statement

Most Q&A systems over documents suffer from hallucinations, unclear sourcing, or unverifiable answers—especially when used on private or proprietary content.

**GroundedAI** is designed to solve this by enforcing strict grounding rules:

The system must:

* Answer **only** using retrieved document content
* Provide **verifiable evidence** (document + chunk/page)
* Refuse when an answer is not supported by the documents

**Primary goal (V1):**
Build a reliable ingestion → chunking → embedding → retrieval pipeline that enables **high-quality, grounded answers**.

---

## What GroundedAI Solves

* ❌ Eliminates hallucinated answers
* 📌 Makes every answer traceable and auditable
* 🔒 Enables safe Q&A over private documents
* 🧠 Improves trust and usability of RAG systems

---

## System Architecture

### High-Level Components

* **Frontend**

  * Vite + React SPA
  * Workspace management, document upload, preview, and chat
* **Backend API**

  * FastAPI service handling auth, workspaces, documents, embeddings, retrieval, and answers
* **Database**

  * PostgreSQL + pgvector
  * Stores document metadata, chunks, embeddings, summaries, and chat history
* **Object Storage**

  * Supabase Storage for original uploaded files
* **LLM & Embeddings**

  * Azure OpenAI
  * Chat completions for answers & summaries
  * Embeddings for semantic retrieval

---

## Product Flow

### A) Guest Session & Workspace Management

1. User clicks **“Let’s Go”** on the landing page.
2. Frontend calls `POST /auth/guest`.
3. Backend creates a guest session and returns a session ID.
4. Session ID is stored client-side and sent via `x-guest-session` header.
5. User creates workspaces via `POST /workspaces`.

**Limits (enforced in API):**

* Max **5 workspaces** per guest
* Max **10 documents** per workspace

---

### B) Document Upload & Processing (Synchronous)

1. User uploads a file from the dashboard.
2. Frontend calls:

   ```
   POST /documents/upload?workspace_id=...
   ```
3. Backend performs:

   * File validation (type + size)
   * Upload to Supabase Storage
   * Document metadata creation in Postgres
   * Text extraction into pages
   * Token-aware chunking with overlap
   * Chunk persistence in Postgres (without embeddings yet)

**Supported file types:**

* PDF
* TXT
* DOCX
* PPTX
* CSV

**Max file size:** 10 MB

---

### C) Embeddings Generation (Explicit Step)

1. Frontend triggers:

   ```
   POST /documents/{document_id}/embed
   ```
2. Backend:

   * Batches chunk text
   * Calls Azure OpenAI embeddings
   * Stores vectors using pgvector
3. Document status transitions:

   * `uploaded` → `embedding` → `embedded`
   * or `failed_embedding` on error

---

### D) Summarization (On-Demand)

1. Frontend calls:

   ```
   POST /documents/{document_id}/summary
   ```
2. Backend:

   * Builds a bounded context from document chunks
   * Calls Azure OpenAI to generate:

     * Bullet takeaways (5–10)
     * Narrative summary (1–3 paragraphs)
     * Suggested questions (5–8)
3. Output is validated and persisted.

Summary retrieval:

```
GET /documents/{document_id}/summary
```

---

### E) Question Answering (RAG with Strict Grounding)

1. User submits a question in the chat panel.
2. Frontend calls:

   ```
   POST /answer
   ```
3. Backend pipeline:

   * Embed the query
   * Retrieve top-K chunks via pgvector similarity
   * Apply adaptive cutoff
   * Build a bounded context window
   * Call Azure OpenAI with **strict JSON-only output rules**
4. Response includes:

   * Answer text
   * Citations (document ID, chunk index, page range, snippet)
5. If unsupported, the system **refuses** and logs the refusal.

All interactions are saved to chat history.

---

## Document Preview & Citations

* All documents are previewed consistently as **PDFs**
* Original files are never modified
* Citations are:

  * Highlighted directly in the document preview
  * Linked to the exact source span
* This provides a **Drive-like preview experience** regardless of original file type

---

## Limits & Statuses

### Document Statuses

* `uploaded`
* `embedding`
* `embedded`
* `failed_embedding`

### Summary Statuses

* `not_started`
* `running`
* `completed`
* `failed`

---

## Tech Stack

### Frontend

* Vite
* React + TypeScript
* React Router
* pdfjs-dist (PDF rendering)
* CSS (page-level, modular styling)

### Backend

* FastAPI
* SQLAlchemy
* pgvector
* httpx
* python-multipart

### Storage & Data

* PostgreSQL
* Supabase Storage

### LLM & Embeddings

* Azure OpenAI (Chat + Embeddings)

---

## Repository Layout

```
frontend/   # Vite + React SPA
backend/    # FastAPI service
```

---

## API Surface (Summary)

* `POST /auth/guest`
* `GET /workspaces`
* `POST /workspaces`
* `POST /documents/upload`
* `GET /documents?workspace_id=...`
* `GET /documents/{id}/file-url`
* `GET /documents/{id}/chunks`
* `POST /documents/{id}/embed`
* `POST /documents/{id}/summary`
* `GET /documents/{id}/summary`
* `POST /query`
* `POST /answer`
* `GET /documents/{id}/chat`

---

## Environment Variables

### Backend

```
DATABASE_URL
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_STORAGE_BUCKET
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_CHAT_DEPLOYMENT
AZURE_OPENAI_CHAT_API_VERSION
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT
AZURE_OPENAI_EMBEDDINGS_API_VERSION
```

---

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Design Principles

* Grounding over generation
* Citations are mandatory
* Predictability over cleverness
* Backend owns correctness
* Frontend prioritizes clarity
