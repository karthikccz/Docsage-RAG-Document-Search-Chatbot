# Docsage — RAG Document Search Chatbot (100% free, runs locally)

Chat with your own PDFs. Upload a document, ask a question in plain English,
and get an answer grounded in that document, with page-level citations.

**Every model in this build runs on your own machine. No OpenAI key, no
Pinecone account, no billing of any kind.**

## Architecture in one paragraph

A PDF is split into overlapping text chunks, each chunk is turned into a
vector (an embedding) that captures its meaning, and all vectors are stored
in a ChromaDB collection on disk. When you ask a question, the question is
embedded the same way, Chroma finds the chunks whose vectors are closest to
it, and those chunks are stuffed into a prompt sent to a local LLM, which
answers using only that context. That's Retrieval-Augmented Generation:
retrieval (Chroma) + generation (the LLM), instead of relying on the model's
memory alone.

```
PDF upload ──► chunk ──► embed (local) ──► Chroma collection
                                                  │
question ──► embed (local) ──────► search ───────┘
                                                  │
                                  top-k chunks + question
                                                  │
                                  local LLM (Ollama) prompt
                                                  │
                                          grounded answer
```

## Stack — and what's free about each piece

| Layer        | Tech                                    | Cost                                    |
|--------------|------------------------------------------|------------------------------------------|
| Frontend     | React (Vite) + Tailwind CSS               | free, runs in your browser               |
| Backend      | FastAPI                                   | free, runs on your machine               |
| Embeddings   | `sentence-transformers/all-MiniLM-L6-v2` via Hugging Face | free, downloads once (~90MB), then runs locally on CPU |
| Chat model   | Ollama, default model `llama3.2`          | free, downloads once (~2GB), then runs locally |
| Vector DB    | ChromaDB                                  | free, just a folder on disk              |

No API key fields exist anywhere in this codebase — there's nothing to pay for.

## Project layout

```
rag-document-search/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI routes
│   │   ├── config.py            Settings (model names, ports — no keys)
│   │   ├── schemas.py           Request/response models
│   │   ├── document_processor.py  PDF loading + chunking
│   │   ├── vector_store.py      Chroma collection read/write
│   │   └── rag_chain.py         Retrieval + prompt + generation via Ollama
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/          FileUpload, Sidebar, ChatWindow, MessageBubble
    │   ├── api/client.js        fetch wrappers for the backend
    │   └── App.jsx
    ├── package.json
    ├── Dockerfile               (used for docker-compose; not needed for Vercel)
    └── vercel.json
```

## 0. Install Ollama (one-time, ~2 minutes)

Ollama is the free local runtime that serves the chat model.

1. Download it from **https://ollama.com** (Mac, Windows, Linux all supported)
   and install it like any other app. It runs as a background service
   automatically after install — you don't need to start anything manually.
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
   This downloads ~2GB once. `llama3.2` (3B parameters) is a good default —
   it runs comfortably on 8GB of RAM. If your machine has more headroom and
   you want noticeably better answers, swap to a bigger model:
   ```bash
   ollama pull llama3.1        # 8B, needs ~8-16GB RAM, better reasoning
   ```
   and update `OLLAMA_MODEL` in `backend/.env` to match. If your machine is
   tight on RAM, go the other way:
   ```bash
   ollama pull llama3.2:1b     # 1B, runs on almost anything
   ```
3. Sanity-check it's running: `ollama list` should show the model you pulled.

## 1. Run the backend locally

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`pip install` will take a few minutes the first time — `sentence-transformers`
pulls in PyTorch, which is a large package even in its CPU-only form. This is
the one-time cost of not paying per API call later.

```bash
cp .env.example .env       # defaults are fine as-is; no key to add
uvicorn app.main:app --reload --port 8000
```

The very first PDF you upload will trigger a one-time ~90MB download of the
embedding model from Hugging Face. After that, everything runs offline.

Visit `http://localhost:8000/docs` — FastAPI's auto-generated Swagger UI lets
you try `/api/upload` and `/api/chat` without touching the frontend yet.

**What each backend file is actually doing:**

- `document_processor.py` — `PyPDFLoader` reads the PDF page by page.
  `RecursiveCharacterTextSplitter` then cuts those pages into ~1000-character
  chunks with 150 characters of overlap, so a sentence that straddles a chunk
  boundary still appears intact in at least one chunk. Every chunk keeps the
  page number it came from in its metadata — that's what powers the "p.4"
  citations later.
- `vector_store.py` — turns chunks into vectors with a local sentence-transformer
  model (no network call after the first download), stores them in a Chroma
  collection, which persists to disk automatically — no explicit save step,
  unlike FAISS. A small `registry.json` tracks each `doc_id`'s filename and
  chunk count, which is what the sidebar's document list reads from.
- `rag_chain.py` — given a question, asks Chroma for the `k` most similar
  chunks, formats them into a context block, and sends a strict system prompt
  ("answer only from this context, say so if it's not here") to the local
  Ollama model. This is the line that actually defends against hallucination —
  the model is told not to use outside knowledge. If Ollama isn't running or
  the model hasn't been pulled, this returns a clear error message instead of
  crashing.
- `main.py` — three real endpoints: `POST /api/upload`, `GET /api/documents`,
  `POST /api/chat`. CORS is configured so only the origins you list in
  `ALLOWED_ORIGINS` can call the API from a browser.

## 2. Run the frontend locally

```bash
cd frontend
npm install
cp .env.example .env       # VITE_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`. Drop a PDF into the sidebar, wait for "Indexed…",
and start asking questions. Each answer shows small chips like
`resume.pdf · p.3` — hover one to see the exact chunk text the model used,
so you can sanity-check the answer against the source.

**Why the scope selector matters:** the chat box can search either "All
documents" or one document at a time (`activeDocId` in `App.jsx`, passed
through as `doc_id` to `/api/chat`). Behind the scenes that becomes a Chroma
metadata filter (`filter={"doc_id": ...}`) in `vector_store.get_retriever`, so
the same collection serves both single-document and cross-document Q&A
without duplicating storage.

## 3. Run everything together with Docker Compose

```bash
docker compose up --build
```

This starts three containers: `ollama` (the model server), `backend`
(FastAPI + Chroma, persisted to `./backend/storage` via a volume mount), and
`frontend` (a Vite production build served by nginx). The first time, pull
the model into the Ollama container:

```bash
docker compose exec ollama ollama pull llama3.2
```

Note: the backend image is large (a few GB) because it bundles PyTorch for
the embedding model — that's the trade-off for zero API cost.

## 4. Deploying this for real — an honest note

The frontend deploys to Vercel exactly as you'd expect:

```bash
cd frontend
vercel
```

The backend is the part worth being upfront about: **Ollama needs a real,
always-on machine with enough RAM** to hold the model in memory. Typical
serverless/free-tier hosts (Vercel functions, AWS Lambda, Render's free web
service tier) either can't run a persistent background process like Ollama or
don't have the RAM for it. Realistic options:

- **A small VPS you control** (a $5-10/month box from DigitalOcean, Hetzner,
  etc.) running both Ollama and the FastAPI backend via `docker compose up`.
  This is genuinely free of *API* costs — you're just paying for a server,
  the same as you would for any backend.
- **Keep it local for development and demos** (e.g. recording a screen capture
  or doing a live walkthrough in an interview) and only deploy the frontend.
  This is a completely normal thing to do for a portfolio project, and it's
  honest about what the project is.
- **Swap back to a hosted LLM API for the deployed version only**, while
  keeping local models for development — only `rag_chain.py` would need a
  different `_llm`. You'd then have a project that demonstrates both
  approaches, which is its own talking point.

## Things worth hardening before this is a "real" product

- **Auth** — right now any visitor can upload to and query the shared index.
  Add user accounts and scope `doc_id`s per user.
- **Bigger files** — very large PDFs will produce thousands of chunks; for
  production, move chunking off the request thread (a background job/queue)
  so uploads don't block on slow embedding.
- **Streaming answers** — Ollama supports streaming; swap the chain's
  `.invoke()` for `.stream()` and use server-sent events so answers appear
  token-by-token instead of all at once.
- **Concurrent requests** — Ollama serves one model at a time per machine by
  default; under real concurrent load you'd want a queue or a beefier host.
