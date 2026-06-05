
# 🎓 TutorAI: Agentic Learning Platform for IIT-JEE Preparation

![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

> TutorAI is an AI-powered learning platform designed specifically for IIT-JEE aspirants. Unlike traditional doubt-solving chatbots, TutorAI acts as a personalized digital mentor capable of teaching concepts, evaluating understanding, generating adaptive study plans, creating assessments, visualizing difficult topics, and orchestrating specialized AI agents through LangGraph and the Model Context Protocol (MCP).

---

## 🚀 Core Vision

Most educational AI systems merely answer questions. **TutorAI focuses on:**

* **Teaching** core concepts from the ground up.
* **Evaluating** understanding through active recall and explanation.
* **Tracking** long-term progress and knowledge gaps.
* **Adapting** future lessons based on performance.
* **Creating** highly personalized, dynamic learning journeys.

---

## ✨ Key Features

### 🧠 Dynamic Mixture-of-Experts (MoE)

Questions are routed to specialized Physics, Chemistry, and Mathematics adapters using a lightweight semantic router, ensuring domain-accurate reasoning.

### 👁️ Multimodal Vision Intelligence

Powered by **Qwen2.5-VL**, the platform seamlessly processes visual inputs:

* Textbook images & diagrams
* Handwritten solutions
* Complex mathematical notation
* OCR text extraction

### 🤖 Agentic Learning System

Built on **LangGraph**, the system orchestrates a swarm of specialized agents:

* **Tutor Agent:** Delivers core instruction.
* **Quiz Agent:** Generates real-time questions.
* **Roadmap Agent:** Dynamically adjusts the syllabus.
* **Visualizer Agent:** Creates graphical representations.
* **Research Agent:** Pulls external information via MCP.
* **Progress & Memory Agents:** Track states and historical performance.

### 🗺️ Adaptive Learning Roadmaps

Automatically generates and adjusts personalized study paths based on continuous assessments.

> *Example Path:* `Recursion` → `Memoization` → `1D DP` → `Knapsack` → `Digit DP` → `Tree DP`

### 🔄 Teach-Back Evaluation

Flipping the script, students explain concepts back to the system. TutorAI evaluates:

* Concept coverage & missing ideas
* Student confidence levels
* Underlying misconceptions

### 📊 Visual Learning Engine

Generates real-time visual aids including graph visualizations, physics diagrams, mathematical plots, tree traversals, DP table walkthroughs, and concept maps.

### 💾 Long-Term Learning Memory

Stores comprehensive student profiles to enable highly personalized tutoring:

* Weak chapters vs. Strong topics
* Historical mistakes & Assessment scores
* Learning velocity trends

---

## 🔌 MCP Tool Ecosystem

TutorAI extends its capabilities by connecting to external tools via the **Model Context Protocol (MCP)**.

| Tool Category | Capabilities |
| --- | --- |
| **Research** | Web Search, PDF Analyzer, Document Retrieval |
| **Media** | YouTube Lecture Finder |
| **Interactive** | Code Execution, Graph Generator, Whiteboard Tools |

---

## 📝 Assessment Engine & Analytics

**Comprehensive Testing:**

* Chapter tests & Adaptive quizzes
* Full mock exams & Time-based tests
* Weakness-targeted assessments

**Performance Analytics:**
Tracks subject performance, chapter mastery, learning velocity, test history, and weak-topic trends over time to continuously calibrate the `Roadmap Agent`.

---

## 🛠️ Tech Stack

| Layer | Technologies |
| --- | --- |
| **Frontend** | React, Vite, TailwindCSS, Framer Motion, React Flow, KaTeX |
| **Backend** | FastAPI, LangChain, LangGraph, FastMCP |
| **AI Stack** | Phi-4 Mini, LoRA Adapters, Qwen2.5-VL, Sentence Transformers, RAG Pipelines |
| **Data Layer** | Supabase, PostgreSQL, Redis |
| **Frameworks** | LangGraph (Agentic Workflow), MCP (Tool Calling), State Persistence |

---

## 🔮 Future Roadmap

* [ ] **Voice Tutor:** Real-time conversational teaching interactions.
* [ ] **Interactive Whiteboard:** Collaborative visual problem-solving workspace.
* [ ] **AI Study Planner:** Automated, calendar-integrated scheduling.
* [ ] **Peer Learning Groups:** AI-moderated study cohorts for group learning.
* [ ] **Interview Preparation Mode:** Specialized technical and conceptual drilling.
* [ ] **Olympiad & Competitive Programming Coach:** Advanced algorithmic training.
* [ ] **Personalized Revision Agent:** Automated spaced-repetition scheduling based on memory decay models.(Requires GPU with 6GB+ VRAM for full MoE + Vision capability)
2.  **Frontend:** `npm run dev`
