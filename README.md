# 🎓 TutorAI

> **An agentic AI tutoring system for JEE/NEET students** — multi-agent LangGraph architecture, personalised mastery tracking, adaptive quizzes, visual learning, and a full analytics dashboard.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-purple)
![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google)

---

## ✨ Features

### 🤖 Multi-Agent Architecture (LangGraph)
TutorAI runs a **LangGraph** state-graph with specialised nodes:

| Agent | Role |
|:---|:---|
| **Router** | Classifies intent and routes to the right specialist |
| **Tutor** | Gemini-powered step-by-step explanations with MoE subject routing |
| **Memory** | Persists conversation history and updates topic mastery |
| **Quiz** | Generates adaptive MCQs targeting weak topics |
| **Roadmap** | Creates personalised study plans with chapter dependencies |
| **Teach-Back** | Evaluates student explanations and scores conceptual understanding |
| **Visualizer** | Generates interactive SVG flowcharts, DP tables, and math plots |
| **Research** | Live web + YouTube search via LangChain tools |

### 🧠 Student Profile & Mastery Engine
- **`get_student_profile`** — full profile with goal and mastery map
- **`update_mastery_score`** — upserts per-topic scores after every session
- **`get_weak_topics`** — returns topics with score < 60 for targeted practice
- **`get_learning_context`** — aggregates goal, recent topics, weak/strong areas for personalisation
- Powered by an internal **FastMCP** stdio server called `tutor_mcp`

### 📊 Analytics Dashboard (Phase 8)
- **Mastery Radar Chart** — pure SVG polygon showing Physics / Chemistry / Maths strength
- **Topic Mastery Heatmap** — filterable colour grid (red → orange → yellow → green)
- **Learning Velocity Sparkline** — avg mastery gain per day over 7 days
- **Session History Table** — topic, duration, score before/after, delta
- **Summary Stats** — Topics Mastered · Streak · Sessions · Avg Mastery

### 📚 PDF Knowledge Base (Vector Search)
- Upload lecture notes or textbook PDFs
- Chunked (500 chars / 100 overlap) and embedded via **Gemini `text-embedding-004`** (768-dim)
- Stored in **Supabase pgvector** with cosine similarity RPC `match_pdf_chunks()`
- Async indexing via **FastAPI BackgroundTasks** — upload returns instantly

### 🧪 Quiz Agent
- Adaptive difficulty based on mastery scores
- Questions sourced from curated JEE/NEET dataset (LaTeX rendered by Qwen2.5-VL)
- Per-topic scoring updates the mastery engine after each submission

### 🗺️ Roadmap Agent
- Generates chapter-by-chapter study plans
- Embeds prerequisite dependency ordering
- Tied to student's exam goal (JEE Main / Advanced / NEET)

### ✏️ Teach-Back Mode
- Triggered when a student explains a concept back to the AI
- AI evaluates correctness, scores it 0–100, and highlights misconceptions
- Score feeds directly into `update_mastery_score`

### 🎨 Visualizer Agent
- **Flowcharts** rendered with React Flow
- **DP Tables** — animated step-by-step matrix filling
- **Function Plots** — SVG curve rendering with interactive hover crosshair

### 📸 Vision OCR
- Upload handwritten or printed problem images
- Primary: **Gemini Vision** (`gemini-2.0-flash`) extracts LaTeX + text
- Fallback: **Qwen2.5-VL** local model for offline capability
- Auto-forwarded to the AI chat for solving

### ✏️ Whiteboard
- Freehand canvas drawing panel
- Neon brush palette, undo/clear
- Saved to Supabase `whiteboard_sketches` table via MCP

### 🔍 Research Tools (LangChain)
- **Web Search** — SerpAPI / DuckDuckGo fallback
- **YouTube Search** — finds video explanations on-demand
- **Code Executor** — sandboxed Python snippet runner

### 💾 Memory & Persistence
- **Redis** in-memory cache (falls back gracefully if unavailable)
- **Supabase** Postgres for all persistent data
- Conversation summaries for long-term context

---

## 🏗️ Architecture

```
Frontend (React + Vite)
    │
    ▼
FastAPI Backend
    │
    ├── LangGraph Agent Graph
    │     ├── Router Node
    │     ├── Tutor Node  ──────────────── Gemini Flash
    │     ├── Quiz Node
    │     ├── Roadmap Node
    │     ├── Teach-Back Node
    │     ├── Visualizer Node ──────────── React Flow / SVG
    │     ├── Research Node   ──────────── LangChain Tools
    │     └── Memory Node
    │
    ├── Internal FastMCP Server  ──────── tutor_mcp (stdio)
    │     ├── get_student_profile
    │     ├── update_mastery_score
    │     ├── get_weak_topics
    │     ├── get_learning_context
    │     ├── search_pdf (pgvector)
    │     └── save_sketch / load_sketches
    │
    ├── Redis Cache  (optional)
    └── Supabase (Postgres + pgvector)
          ├── profiles
          ├── conversations / messages
          ├── topic_mastery
          ├── pdf_documents / pdf_chunks (vector)
          ├── learning_sessions
          └── whiteboard_sketches
```

---

## 🗄️ Database Schema

| Table | Purpose |
|:---|:---|
| `profiles` | Student name, grade, exam goal |
| `conversations` | Chat sessions per subject |
| `messages` | Individual messages with topic tags |
| `topic_weakness` | Error-rate tracking per topic |
| `topic_mastery` | Mastery scores (0–100) per topic |
| `pdf_documents` | Uploaded PDF metadata |
| `pdf_chunks` | 500-char chunks with `vector(768)` embeddings |
| `learning_sessions` | Session start/end, score before/after |
| `whiteboard_sketches` | Freehand canvas SVG paths |

---

## 🚀 Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase project with pgvector enabled
- Google AI API key (Gemini)
- Redis (optional, falls back to in-memory)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Fill in: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, FRONTEND_URL

# Run database migrations
# Apply supabase/migrations/*.sql in your Supabase SQL editor

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Create .env
echo "VITE_API_URL=http://localhost:8000" > .env
echo "VITE_SUPABASE_URL=your_supabase_url" >> .env
echo "VITE_SUPABASE_ANON_KEY=your_anon_key" >> .env

npm run dev
```

---

## 📁 Project Structure

```
TutorAI/
├── backend/
│   └── app/
│       ├── core/          # Config, Supabase client
│       ├── middleware/     # JWT auth
│       ├── models/         # Pydantic schemas
│       ├── routers/        # FastAPI routes (chat, quiz, profile, ocr, analytics, roadmap)
│       ├── services/       # Agent, LLM, MCP, PDF, History, Weakness services
│       └── mcp_servers/    # Internal FastMCP server (tutor_mcp)
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── auth/       # Login, ProtectedRoute
│       │   ├── chat/       # ChatWindow, MessageBubble, MessageInput, Whiteboard
│       │   ├── quiz/       # QuizCard, ResultScreen
│       │   ├── shared/     # Navbar (sidebar), SubjectBadge
│       │   └── visualizer/ # Flowchart, DPTable, FunctionPlot
│       ├── pages/          # Dashboard, Chat, Quiz, Analytics, Vision OCR, Profile
│       ├── hooks/          # useChat, useAuth, useWeakness
│       ├── store/          # Zustand auth store
│       └── lib/            # Axios API client
├── supabase/
│   └── migrations/        # SQL schema + pgvector setup
├── preprocessing/          # Dataset preparation scripts
└── requirements.txt
```

---

## 🔑 Environment Variables

### Backend `.env`
```
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
FRONTEND_URL=http://localhost:5173
PORT=8000
REDIS_URL=redis://localhost:6379   # optional
SERPAPI_KEY=                        # optional, for web search
```

### Frontend `.env`
```
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit with concise messages: `git commit -m "feat: add X"`
4. Open a pull request

---

## 📄 License

MIT © 2026 TutorAI
