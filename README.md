# Docsage — RAG Document Search Chatbot

Chat with your own PDFs using a fully local, free AI stack.
Upload a document, ask anything, get a grounded answer with page-level citations.

**No OpenAI key. No Pinecone account. No billing. Runs entirely on your machine.**

---

## What's inside

| Layer | Tech | Cost |
|---|---|---|
| Frontend | React (Vite) + Tailwind CSS | Free |
| Backend | FastAPI | Free |
| Embeddings | `all-MiniLM-L6-v2` via Hugging Face | Free, ~90MB one-time download |
| Sparse search | BM25 (`rank_bm25`) | Free |
| Vector DB | ChromaDB (local, on disk) | Free |
| Reranker | `ms-marco-MiniLM-L-6-v2` CrossEncoder | Free, ~90MB one-time download |
| Chat model | Ollama — `llama3.2` | Free, ~2GB one-time download |

---

## How it works

### Indexing (happens once per PDF upload)

```
PDF upload
  → PyPDFLoader reads each page
  → RecursiveCharacterTextSplitter cuts into ~1000-char overlapping chunks
  → HuggingFaceEmbeddings converts each chunk to a dense vector
  → Chroma stores the vectors on disk
  → BM25 corpus JSON updated for keyword search
```

### Answering a question (happens every time you ask)

```
Question
  → Dense search  : Chroma finds top 10 semantically similar chunks
  → Sparse search : BM25 finds top 10 keyword-matching chunks
  → RRF fusion    : Reciprocal Rank Fusion merges both lists into one
  → Reranker      : CrossEncoder scores every chunk vs the question, keeps top 4
  → LLM prompt    : top 4 chunks + question → Ollama (llama3.2)
  → Answer        : grounded in your document, with page citations
```

### Why hybrid search + reranking?

| Technique | Problem it solves |
|---|---|
| Dense (Chroma) | Finds meaning even when the wording is different |
| Sparse (BM25) | Catches exact keyword matches dense search can miss |
| RRF | Merges both ranked lists without needing to tune score weights |
| CrossEncoder reranker | Re-reads query + chunk together — more accurate than cosine similarity alone |

---

## Project structure

```
rag-document-search/
├── .gitignore
├── docker-compose.yml
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py               FastAPI routes (/upload, /documents, /chat)
│       ├── config.py             All settings — model names, chunk size, k values
│       ├── schemas.py            Request/response Pydantic models
│       ├── document_processor.py PDF loading and chunking
│       ├── vector_store.py       Hybrid search: Chroma + BM25 + RRF
│       └── rag_chain.py          Reranker + prompt + Ollama generation
└── frontend/
    ├── Dockerfile
    ├── vercel.json
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── App.jsx               Root state and wiring
        ├── api/client.js         fetch wrappers for the backend
        └── components/
            ├── Sidebar.jsx       Upload dropzone + document scope list
            ├── ChatWindow.jsx    Message list + input bar
            ├── MessageBubble.jsx Answer bubbles with page citation chips
            └── FileUpload.jsx    Drag-and-drop PDF uploader
```

---

## Running locally

### Prerequisites (one-time installs)

1. **Python 3.10+** — python.org
2. **Node.js 18+** — nodejs.org
3. **Ollama** — ollama.com → install → then pull the model:
   ```bash
   ollama pull llama3.2
   ```

### Backend

```bash
cd backend

# create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate

# install dependencies (takes a few minutes — pulls PyTorch)
pip install -r requirements.txt

# copy config (no keys to fill in — defaults work as-is)
cp .env.example .env              # Windows: copy .env.example .env

# start the API server
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` to confirm the API is running.

> **Note:** The very first PDF upload triggers a one-time ~90MB download of
> the embedding model and reranker from Hugging Face. After that, everything
> runs fully offline.

### Frontend (new terminal)

```bash
cd frontend
npm install
cp .env.example .env              # Windows: copy .env.example .env
npm run dev
```

Open `http://localhost:5173` — upload a PDF, ask questions.

---

## Running with Docker (recommended)

Runs backend + frontend + Ollama together with one command.
Requires **Docker Desktop** installed and running.

```bash
# from project root
docker compose up --build
```

First time only — pull the model into the Ollama container:
```bash
# in a second terminal, while compose is running
docker compose exec ollama ollama pull llama3.2
```

Open `http://localhost:5173`.

### Useful Docker commands

```bash
docker compose up           # start (after first build)
docker compose down         # stop everything
docker compose logs backend # debug backend errors
docker compose ps           # check all 3 containers are running
```

---

## Sharing with someone else (Docker Hub)

Build and push your images so anyone with Docker can run it without
installing Python or Node:

```bash
docker build -t yourusername/docsage-backend:v1 ./backend
docker build -t yourusername/docsage-frontend:v1 ./frontend
docker push yourusername/docsage-backend:v1
docker push yourusername/docsage-frontend:v1
```

Your friend creates a folder with this `docker-compose.yml` (replacing
`yourusername` with your Docker Hub username):

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

Then:
```bash
docker compose up
docker compose exec ollama ollama pull llama3.2
# open http://localhost:5173
```

---

## Deploying to production

### Frontend → Vercel

```bash
cd frontend
vercel
```

Set environment variable in Vercel dashboard:
```
VITE_API_URL=https://api.yourdomain.com
```

### Backend → any VPS (Hetzner, DigitalOcean, etc.)

```bash
# on the server
curl -fsSL https://get.docker.com | sh
git clone https://github.com/yourusername/rag-document-search.git
cd rag-document-search
docker compose up -d
docker compose exec ollama ollama pull llama3.2
```

Set up Caddy for HTTPS:
```
# /etc/caddy/Caddyfile
api.yourdomain.com {
    reverse_proxy localhost:8000
}
```

Update `backend/.env` on the server:
```
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

---

## Configuration

All tunable values are in `backend/app/config.py`:

| Setting | Default | What it controls |
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

## API endpoints

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/upload` | Upload and index a PDF |
| `GET` | `/api/documents` | List all indexed documents |
| `POST` | `/api/chat` | Ask a question (optional `doc_id` to scope to one file) |

Full interactive docs at `http://localhost:8000/docs`.

---

## Security checklist before going public

- [ ] `.gitignore` excludes `.env` and `storage/` — already in place
- [ ] `backend/.env` is never committed — confirmed
- [ ] `ALLOWED_ORIGINS` is set to your real frontend URL on the server
- [ ] No API keys in the codebase — confirmed (none needed)
- [ ] Test PDFs in `storage/uploads/` are cleared before pushing to GitHub

---

## Troubleshooting

**"Couldn't reach Ollama"**
→ Ollama isn't running, or you haven't pulled the model.
Run `ollama list` — if `llama3.2` isn't there, run `ollama pull llama3.2`.

**First upload is slow**
→ Normal. Hugging Face is downloading the embedding model and reranker (~180MB total). One-time only.

**`{"detail":"Not Found"}` at localhost:8000**
→ The backend is running fine. Visit `/docs` not `/` for the API page.

**Frontend can't reach backend**
→ Check `VITE_API_URL` in `frontend/.env` matches where uvicorn is running.

**Docker: "port already in use"**
→ Something else is using 8000 or 5173. Run `docker compose down` then `docker compose up` again.#   D o c s a g e - R A G - D o c u m e n t - S e a r c h - C h a t b o t  
 