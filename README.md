
# 📄 Docsage — RAG Document Search Chatbot

Chat with your own PDFs using a fully local, free AI stack.

Upload a document, ask anything, and get a grounded answer with page-level citations.

> **No OpenAI key. No Pinecone account. No billing. Runs entirely on your machine.**

---

## 📑 Table of Contents

- [What's Inside](#-whats-inside)
- [How It Works](#-how-it-works)
  - [Indexing](#1-indexing)
  - [Answering a Question](#2-answering-a-question)
- [Why Hybrid Search + Reranking?](#-why-hybrid-search--reranking)
- [Project Structure](#-project-structure)
- [Running Locally](#-running-locally)
  - [Prerequisites](#1-prerequisites-one-time-installs)
  - [Backend Setup](#2-backend-setup)
  - [Frontend Setup](#3-frontend-setup)
- [Running with Docker](#-running-with-docker-recommended)
- [Sharing with Someone Else](#-sharing-with-someone-else-docker-hub)
- [Deploying to Production](#-deploying-to-production)
- [Configuration](#-configuration)
- [API Endpoints](#-api-endpoints)
- [Security Checklist](#-security-checklist-before-going-public)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 What's Inside

| Layer | Technology | Cost |
|---|---|---|
| Frontend | React (Vite) + Tailwind CSS | Free |
| Backend | FastAPI | Free |
| Embeddings | `all-MiniLM-L6-v2` via Hugging Face | Free, ~90MB one-time download |
| Sparse Search | BM25 (`rank_bm25`) | Free |
| Vector Database | ChromaDB (local, on disk) | Free |
| Reranker | `ms-marco-MiniLM-L-6-v2` CrossEncoder | Free, ~90MB one-time download |
| Chat Model | Ollama — `llama3.2` | Free, ~2GB one-time download |

---

## ⚙️ How It Works

### 1. Indexing

*Happens once per PDF upload.*

```text
PDF upload
    ↓
PyPDFLoader reads each page
    ↓
RecursiveCharacterTextSplitter cuts into
~1000-character overlapping chunks
    ↓
HuggingFaceEmbeddings converts each chunk
to a dense vector
    ↓
Chroma stores the vectors on disk
    ↓
BM25 corpus JSON updated for keyword search
```

### 2. Answering a Question

*Happens every time you ask.*

```text
Question
    ↓
Dense Search
Chroma finds top 10 semantically similar chunks
    ↓
Sparse Search
BM25 finds top 10 keyword-matching chunks
    ↓
RRF Fusion
Reciprocal Rank Fusion merges both lists into one
    ↓
Reranker
CrossEncoder scores every chunk vs the question
and keeps the top 4
    ↓
LLM Prompt
Top 4 chunks + question
    ↓
Ollama (llama3.2)
    ↓
Answer
Grounded in your document, with page citations
```

---

## 🔍 Why Hybrid Search + Reranking?

| Technique | Problem It Solves |
|---|---|
| Dense (Chroma) | Finds meaning even when the wording is different |
| Sparse (BM25) | Catches exact keyword matches dense search can miss |
| RRF | Merges both ranked lists without needing to tune score weights |
| CrossEncoder Reranker | Re-reads query + chunk together — more accurate than cosine similarity alone |

---

## 📁 Project Structure

```text
rag-document-search/
│
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   │
│   └── app/
│       ├── main.py
│       │   └── FastAPI routes
│       │       (/upload, /documents, /chat)
│       │
│       ├── config.py
│       │   └── All settings — model names,
│       │       chunk size, k values
│       │
│       ├── schemas.py
│       │   └── Request/response Pydantic models
│       │
│       ├── document_processor.py
│       │   └── PDF loading and chunking
│       │
│       ├── vector_store.py
│       │   └── Hybrid search:
│       │       Chroma + BM25 + RRF
│       │
│       └── rag_chain.py
│           └── Reranker + prompt + Ollama generation
│
└── frontend/
    ├── Dockerfile
    ├── vercel.json
    ├── nginx.conf
    ├── package.json
    │
    └── src/
        ├── App.jsx
        │   └── Root state and wiring
        │
        ├── api/
        │   └── client.js
        │       └── Fetch wrappers for the backend
        │
        └── components/
            ├── Sidebar.jsx
            │   └── Upload dropzone + document scope list
            │
            ├── ChatWindow.jsx
            │   └── Message list + input bar
            │
            ├── MessageBubble.jsx
            │   └── Answer bubbles with page citation chips
            │
            └── FileUpload.jsx
                └── Drag-and-drop PDF uploader
```

---

## 💻 Running Locally

### 1. Prerequisites (One-Time Installs)

1. **Python 3.10+** — [python.org](https://www.python.org/)
2. **Node.js 18+** — [nodejs.org](https://nodejs.org/)
3. **Ollama** — [ollama.com](https://ollama.com/)

Install Ollama, then pull the model:

```bash
ollama pull llama3.2
```

---

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

#### Create and Activate Virtual Environment

```bash
python -m venv venv
```

**Windows:**

```powershell
.\venv\Scripts\Activate
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

> Takes a few minutes — pulls PyTorch.

#### Configure Environment

**Windows:**

```powershell
copy .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

No keys to fill in — defaults work as-is.

#### Start the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit:

```text
http://localhost:8000/docs
```

This confirms the API is running.

> **Note:** The very first PDF upload triggers a one-time ~90MB download of the embedding model and reranker from Hugging Face. After that, everything runs fully offline.

---

### 3. Frontend Setup

Open a **new terminal**:

```bash
cd frontend
```

#### Install Dependencies

```bash
npm install
```

#### Configure Environment

**Windows:**

```powershell
copy .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

#### Start the Frontend

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

Upload a PDF and ask questions.

---

## 🐳 Running with Docker (Recommended)

Runs backend + frontend + Ollama together with one command.

**Requires Docker Desktop installed and running.**

### Start All Services

From the project root:

```bash
docker compose up --build
```

### Pull the Model (First Time Only)

In a second terminal, while Compose is running:

```bash
docker compose exec ollama ollama pull llama3.2
```

Open:

```text
http://localhost:5173
```

---

### Useful Docker Commands

| Command | Purpose |
|---|---|
| `docker compose up` | Start (after first build) |
| `docker compose down` | Stop everything |
| `docker compose logs backend` | Debug backend |
| `docker compose ps` | Check all 3 containers are running |

---

## 📦 Sharing with Someone Else (Docker Hub)

Build and push your images so anyone with Docker can run it without installing Python or Node.

### 1. Build Docker Images

```bash
docker build -t yourusername/docsage-backend:v1 ./backend

docker build -t yourusername/docsage-frontend:v1 ./frontend
```

### 2. Push Images to Docker Hub

```bash
docker push yourusername/docsage-backend:v1

docker push yourusername/docsage-frontend:v1
```

### 3. Docker Compose Configuration

Your friend creates a folder with this `docker-compose.yml`, replacing `yourusername` with your Docker Hub username:

```yaml
version: "3.9"

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  backend:
    image: yourusername/docsage-backend:v1
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - ./storage:/app/storage
    depends_on:
      - ollama

  frontend:
    image: yourusername/docsage-frontend:v1
    ports:
      - "5173:80"
    depends_on:
      - backend

volumes:
  ollama_data:
```

### 4. Run the Application

```bash
docker compose up
```

Pull the Ollama model:

```bash
docker compose exec ollama ollama pull llama3.2
```

Open:

```text
http://localhost:5173
```

---

## ☁️ Deploying to Production

### Frontend → Vercel

Navigate to the frontend directory:

```bash
cd frontend
```

Deploy:

```bash
vercel
```

Set the environment variable in the Vercel dashboard:

```text
VITE_API_URL=https://api.yourdomain.com
```

---

### Backend → Any VPS

Supported examples:

- Hetzner
- DigitalOcean
- Any VPS

#### 1. Install Docker on the Server

```bash
curl -fsSL https://get.docker.com | sh
```

#### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/rag-document-search.git

cd rag-document-search
```

#### 3. Start Docker Compose

```bash
docker compose up -d
```

#### 4. Pull the Ollama Model

```bash
docker compose exec ollama ollama pull llama3.2
```

---

### HTTPS with Caddy

Set up Caddy for HTTPS.

**`/etc/caddy/Caddyfile`**

```text
api.yourdomain.com {
    reverse_proxy localhost:8000
}
```

---

### Backend Environment Configuration

Update `backend/.env` on the server:

```env
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

---

## ⚙️ Configuration

All tunable values are in:

```text
backend/app/config.py
```

| Setting | Default | What It Controls |
|---|---|---|
| `embedding_model` | `all-MiniLM-L6-v2` | Dense embedding model |
| `reranker_model` | `ms-marco-MiniLM-L-6-v2` | CrossEncoder reranker |
| `ollama_model` | `llama3.2` | Chat model (swap to `llama3.1` for better answers) |
| `chunk_size` | `1000` | Characters per chunk |
| `chunk_overlap` | `150` | Overlap between adjacent chunks |
| `dense_top_k` | `10` | Candidates fetched from Chroma |
| `sparse_top_k` | `10` | Candidates fetched from BM25 |
| `rerank_top_n` | `4` | Final chunks passed to the LLM after reranking |

---

## 🔌 API Endpoints

| Method | Endpoint | What It Does |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/upload` | Upload and index a PDF |
| `GET` | `/api/documents` | List all indexed documents |
| `POST` | `/api/chat` | Ask a question (optional `doc_id` to scope to one file) |

### Interactive API Documentation

```text
http://localhost:8000/docs
```

---

## 🔒 Security Checklist Before Going Public

- [ ] `.gitignore` excludes `.env` and `storage/` — already in place
- [ ] `backend/.env` is never committed — confirmed
- [ ] `ALLOWED_ORIGINS` is set to your real frontend URL on the server
- [ ] No API keys in the codebase — confirmed (none needed)
- [ ] Test PDFs in `storage/uploads/` are cleared before pushing to GitHub

---

## 🛠️ Troubleshooting

### "Couldn't reach Ollama"

Ollama isn't running, or you haven't pulled the model.

Run:

```bash
ollama list
```

If `llama3.2` isn't there:

```bash
ollama pull llama3.2
```

---

### First Upload Is Slow

Normal. Hugging Face is downloading the embedding model and reranker (~180MB total).

One-time only.

---

### `{"detail":"Not Found"}` at localhost:8000

The backend is running fine.

Visit:

```text
http://localhost:8000/docs
```

Not `/` for the API page.

---

### Frontend Can't Reach Backend

Check `VITE_API_URL` in `frontend/.env` matches where uvicorn is running.

---

### Docker: "Port Already in Use"

Something else is using `8000` or `5173`.

Run:

```bash
docker compose down
```

Then:

```bash
docker compose up
```

---

## 📌 Project Summary

Docsage is a fully local RAG document search chatbot that combines:

- Dense semantic search with ChromaDB
- Sparse keyword search with BM25
- Reciprocal Rank Fusion (RRF)
- CrossEncoder reranking
- Ollama-powered local LLM generation
- Page-level document citations

No OpenAI key. No Pinecone account. No billing.
Runs entirely on your machine.
