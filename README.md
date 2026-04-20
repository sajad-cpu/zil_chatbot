# RAG Chatbot

A full-stack Retrieval-Augmented Generation chatbot with JWT authentication and persistent chat history. Teach it any text, then ask questions — it answers **only** from what you taught it.

```
User Query -> Embedding -> Vector Search (pgvector) -> Context -> LLM -> Grounded Answer
```

- **Backend** — Python + FastAPI, Gemini API for embeddings, ZilRouter for answer generation, PostgreSQL + pgvector for storage.
- **Frontend** — React + Vite, auth flow, multi-conversation chat UI, teach/train interface.
- **Zero hallucinations** — strict prompt + similarity threshold; off-topic questions get `"I don't know"`.

**Live backend:** https://rag-chatbot-backend-8hyx.onrender.com

---

## Prerequisites

- **Node.js 18+** (for the frontend)
- A free **Gemini API key** — get one at <https://aistudio.google.com/app/apikey>

> **For local backend development only** (not needed if using the hosted backend):
> - Python 3.9+
> - PostgreSQL 14+ with the [pgvector](https://github.com/pgvector/pgvector) extension

---

## Quick Start (Frontend Only — Using Hosted Backend)

The fastest way to run the app. The frontend connects to the deployed backend on Render.

```bash
cd frontend
npm install
```

Create a `.env` file in the `frontend/` directory:

```bash
VITE_BACKEND_URL=https://rag-chatbot-backend-8hyx.onrender.com
```

Start the dev server:

```bash
npm run dev
```

Open <http://localhost:5173>. Sign up, switch to **Teach**, paste some text, then ask questions in **Chat**.

> **Note:** The Render free tier spins down after inactivity. The first request may take 30-60 seconds while the server cold-starts.

---

## Full Local Setup (Backend + Frontend)

### 1. Backend

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` and fill in the required values:

```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql://youruser@localhost:5432/ragchatbot
JWT_SECRET=your_secret_here
ZILROUTER_URL=https://zilrouter.ngrok.app
ZILROUTER_API_KEY=your_zilrouter_api_key_here
```

Set up the database:

```bash
createdb ragchatbot
psql ragchatbot -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Install dependencies and start the server:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```

Verify it's running:

```bash
curl http://localhost:8000/health
# {"ok":true,"service":"rag-chatbot-backend"}
```

API docs: <http://localhost:8000/docs>

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api/*` to `http://localhost:8000` automatically.

---

## Try It

1. Open the app and **sign up** with an email and password.
2. Switch to the **Teach** tab.
3. Paste the contents of [`sample-data.txt`](./sample-data.txt) and click **Train**.
4. Switch to **Chat** and ask:
   - *"Who founded Acme Robotics?"* — grounded answer
   - *"How much does the Picker R3 cost?"* — grounded answer
   - *"Who won the World Cup in 2022?"* — **"I don't know"**

---

## API Endpoints

| Method | Path                      | Auth | Purpose                          |
| ------ | ------------------------- | ---- | -------------------------------- |
| GET    | `/health`                 | No   | Health check                     |
| POST   | `/auth/signup`            | No   | Create account, returns JWT      |
| POST   | `/auth/login`             | No   | Login, returns JWT               |
| GET    | `/auth/me`                | Yes  | Current user info                |
| POST   | `/train`                  | Yes  | Chunk + embed + store text       |
| DELETE | `/train/clear`            | Yes  | Wipe the knowledge base          |
| GET    | `/train/stats`            | No   | Returns `{ totalChunks }`        |
| POST   | `/chat`                   | Yes  | RAG query -> answer + sources    |
| GET    | `/conversations`          | Yes  | List user's conversations        |
| POST   | `/conversations`          | Yes  | Create new conversation          |
| GET    | `/conversations/{id}`     | Yes  | Get conversation with messages   |
| DELETE | `/conversations/{id}`     | Yes  | Delete conversation              |

---

## Project Layout

```
rag-chatbot/
├── backend/
│   ├── main.py                 # FastAPI entrypoint
│   ├── requirements.txt
│   ├── render.yaml             # Render deployment config
│   ├── .env.example
│   ├── auth/
│   │   └── deps.py             # JWT dependency (Bearer token extraction)
│   ├── db/
│   │   ├── pool.py             # Async connection pool (asyncpg + pgvector)
│   │   └── migrations.py       # Auto-creates users, conversations, messages tables
│   ├── routes/
│   │   ├── auth.py             # Signup, login, me
│   │   ├── chat.py             # RAG query flow
│   │   ├── conversations.py    # CRUD for conversations & messages
│   │   └── train.py            # Ingest text into vector store
│   ├── services/
│   │   ├── chunker.py          # Sentence-aware text chunking
│   │   └── gemini.py           # Gemini embeddings + ZilRouter generation
│   └── vector_db/
│       └── store.py            # pgvector-backed cosine similarity store
├── frontend/
│   ├── src/
│   │   ├── api.js              # Fetch wrapper with JWT support
│   │   ├── App.jsx             # Root component (auth + tab routing)
│   │   ├── components/
│   │   │   ├── AuthPage.jsx    # Login / signup form
│   │   │   ├── Chat.jsx        # Chat UI with conversation sidebar
│   │   │   ├── Teach.jsx       # Text training interface
│   │   │   └── ClinicAgent.jsx # Clinic AI agent (separate page)
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── vite.config.js          # Dev proxy config
│   └── package.json
├── sample-data.txt             # Example training data
└── README.md
```

---

## How Grounding Works

Two safeguards prevent hallucinations:

1. **Similarity floor** (`MIN_SCORE = 0.35` in `backend/routes/chat.py`). If no chunk crosses the threshold, the backend returns `"I don't know"` without calling the LLM.
2. **Strict system prompt**:
   ```
   You are a helpful assistant. Answer ONLY using the context below.
   If the answer is not present in the context, reply exactly: "I don't know".
   Do not invent facts. Be concise and direct.
   ```

Tune `MIN_SCORE` and `TOP_K` at the top of `backend/routes/chat.py` to trade recall vs. precision.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable            | Required | Default                          | Description                        |
| ------------------- | -------- | -------------------------------- | ---------------------------------- |
| `GEMINI_API_KEY`    | Yes      | —                                | Google Gemini API key (embeddings) |
| `DATABASE_URL`      | Yes      | —                                | PostgreSQL connection string       |
| `JWT_SECRET`        | Yes      | `dev-secret-key...`              | Secret for signing JWTs            |
| `PORT`              | No       | `8000`                           | Server port                        |
| `FRONTEND_URL`      | No       | `http://localhost:5173`          | Allowed CORS origin                |
| `GEMINI_EMBED_MODEL`| No       | `gemini-embedding-001`           | Embedding model name               |
| `ZILROUTER_URL`     | No       | `https://zilrouter.ngrok.app`    | ZilRouter API base URL             |
| `ZILROUTER_API_KEY` | Yes      | —                                | ZilRouter API key                  |

### Frontend (`frontend/.env`)

| Variable            | Required | Default                          | Description                                 |
| ------------------- | -------- | -------------------------------- | ------------------------------------------- |
| `VITE_BACKEND_URL`  | No       | `/api` (Vite proxy)              | Backend URL. Set for production/hosted use.  |

---

## Deployment

The backend is configured for [Render](https://render.com) via `backend/render.yaml`. Set the environment variables in your Render dashboard and deploy from the repo.

For the frontend, run `npm run build` in `frontend/` and deploy the `dist/` folder to any static hosting (Vercel, Netlify, Render static site, etc.). Set `VITE_BACKEND_URL` to your backend URL at build time.
