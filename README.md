# 🎓 TutorAI

> **An agentic AI tutoring system for JEE/NEET students** — multi-agent LangGraph architecture, personalised mastery tracking, adaptive quizzes, visual learning, and a full analytics dashboard.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-purple)
![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google)

---
[Demo Video Link](https://youtu.be/OvysjiA29Iw)🚀
## ✨ Features

### 🤖 True Multi-Agent Architecture (LangGraph)
TutorAI runs a **native LangGraph StateGraph** where agents are independent graph nodes, and execution routing is handled natively via conditional routing and parallel branches:

| Agent / Node | Type | Role |
|:---|:---|:---|
| **Orchestrator** | LLM | Classifies user intent and routes to the right specialist(s). Implements fast deterministic bypass for active teach-back responses. |
| **Research** | LLM | Fetches live web data and YouTube videos concurrently. No redundant "should I search?" reasoning. |
| **Visual** | LLM | Direct visualization routing: generates flowcharts, DP tables, and math curves. |
| **Tutor** | LLM | ReAct-style agent. Exposes GRPO fine-tuned models (physics_grpo, math_grpo, chemistry_grpo) and note search as tools; LLM naturally selects them. |
| **Critic** | LLM | Evaluates response completeness and accuracy, triggering loop-backs to Research or Tutor when info is missing. |
| **Quiz** | LLM | Sources MCQs matching dynamic student capability and tracked weaknesses. |
| **Teach-Back** | Deterministic | Evaluates student active recall explanations and updates mastery. |
| **Roadmap** | Deterministic | Fetches chapter dependency studies from the database. |
| **Memory** | Deterministic | Resiliently saves logs. Writes weakness snapshots and mastery updates only when state changes. |
| **Composer** | Deterministic | Formats and appends visualization panels, quizzes, and scorecards. |

### 🧠 Student Profile & Mastery Engine
- **`get_student_profile`** — full profile with goal and mastery map
- **`update_mastery_score`** — upserts per-topic scores after every session
- **`get_weak_topics`** — returns topics with score < 60 for targeted practice
- **`get_learning_context`** Aggregates goal, recent topics, weak/strong areas for personalisation
- Powered by an internal **FastMCP** stdio server called `tutor_mcp`

### 📊 Analytics Dashboard (Phase 8)
- **Mastery Radar Chart** — pure SVG polygon showing Physics / Chemistry / Maths strength
- **Topic Mastery Heatmap** — filterable colour grid (red → orange → yellow → green)
- **Learning Velocity Sparkline** — avg mastery gain per day over 7 days
- **Session History Table** — topic, duration, score before/after, delta
- **Summary Stats** — Topics Mastered · Streak · Sessions · Avg Mastery

---

## 🏗️ Multi-Agent Graph Flow

```
                  START
                    │
                    ▼
            orchestrator_node
                    │
         (Conditional Fan-Out Edge)
         ┌──────────┼──────────┐
         ▼          ▼          ▼
     research    visual      quiz
         │          │          │
         ▼          ▼          │
    (Parallel Fan-In Join)     │
         │          │          │
         ▼          ▼          │
            tutor_node         │
                    │          │
                    ▼          │
               critic_node     │
                    │          │
            (Conditional Edge) │
             ├── Approved ─────┼──┐
             └── Needs Info ───┘  │
                    │             │
             (Loop Back to        │
              Research / Tutor)   │
                                  ▼
                             memory_node
                                  │
                                  ▼
                            composer_node
                                  │
                                  ▼
                                 END
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
- Google AI API key (Gemini) or OpenRouter API key
- Redis (optional, falls back to in-memory)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Fill in: LLM_PROVIDER, OPENROUTER_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, FRONTEND_URL

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
LLM_PROVIDER=openrouter               # "openrouter" or "gemini"
OPENROUTER_API_KEY=                 # required if using OpenRouter
GEMINI_API_KEY=                     # required if using Gemini
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
