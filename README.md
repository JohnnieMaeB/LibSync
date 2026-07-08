# 📚 AI Library Assistant — Portfolio Demo

![Status: Active Development](https://img.shields.io/badge/Status-Active_Development-brightgreen)
![Frontend](https://img.shields.io/badge/Frontend-GitHub_Pages-blue)
![Backend](https://img.shields.io/badge/Backend-Render-purple)
![AI](https://img.shields.io/badge/AI-PydanticAI-yellow)
![Vector_DB](https://img.shields.io/badge/Vector_DB-Pinecone-teal)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-lightgrey)


# 🚀 LibSync

**LibSync** is an AI-powered chatbot designed to assist users with library services. Built with a Python/PydanticAI backend and a vanilla JS frontend, LibSync demonstrates a full-stack workflow, cloud deployment, and AI integration.

---

## 🎯 Purpose

LibSync provides a conversational interface for library patrons, enabling natural language questions and helpful responses.
The project is currently in **active development**, focusing on technical experimentation, deployment workflows, and AI capabilities.

---

## 🛠️ Tech Stack

- **Frontend:** Vanilla JavaScript, HTML, CSS
- **Backend:** Python, FastAPI
- **AI Integration:** [PydanticAI](https://ai.pydantic.dev/) agent calling the Hugging Face Inference API (novita provider, `deepseek-ai/DeepSeek-V3.2-Exp`)
- **Vector Database:** Pinecone (for semantic search and retrieval)
- **Package Management:** [uv](https://docs.astral.sh/uv/) for the Python backend and IaC scripts
- **Automation & DevOps:** GitHub Actions for CI/CD and Infrastructure as Code (IaC)
- **Cloud Deployment:** Render

---

## 🧩 Architecture Overview

- **Frontend:** Simple chat UI built with JavaScript, HTML, and CSS (`client/src`, mirrored to `docs/` for GitHub Pages)
- **Backend:** FastAPI server (`server/`) handling requests, rate limiting, and a PydanticAI agent that calls Hugging Face models
- **Vector Layer:** Pinecone stores and retrieves library policies for factual RAG-based answers
- **Automation:** GitHub Actions workflow provisions and updates Pinecone vectors automatically (IaC), via Python scripts in `pinecone-scripts/`
- **Deployment:** Hosted on Render (backend) and GitHub Pages (frontend)

---

## 🏆 Skills Demonstrated

- **Full-Stack Development:** Building and connecting frontend (JS/HTML/CSS) with backend (Python/FastAPI)
- **Agentic AI Integration:** Using PydanticAI to define a typed, testable agent around the Hugging Face Inference API
- **Vector Search & Retrieval:** Implementing Pinecone for RAG workflows and policy-based query retrieval
- **Infrastructure as Code (IaC):** Automating Pinecone vector DB setup and data upserts with GitHub Actions
- **Cloud Deployment:** Deploying backend on Render, frontend on GitHub Pages
- **Environment Configuration & Security:** Managing environment variables and securing API tokens
- **Debugging & Logging:** Implementing request/response logging for monitoring and troubleshooting
- **Project Workflow:** Version control with Git, branching, and automated build/test pipelines
- **UI/UX Design:** Real-time chat interface, responsive and interactive frontend design

---

## ✨ Features

- Real-time chat interface
- PydanticAI-powered responses via Hugging Face
- Cloud deployment for remote access

---

## 💻 Local Setup

### Prerequisites

- **uv** (Python package/project manager — installs its own Python if needed). If `uv` isn't already on your machine:

  ```powershell
  # Windows (PowerShell)
  powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

  The installer prints where it placed `uv.exe` (typically `C:\Users\<you>\.local\bin` on Windows or `~/.local/bin` on macOS/Linux). **Close and reopen your terminal** (or open a new PowerShell/shell window) after installing — the installer updates your PATH, but only takes effect in new terminal sessions. Verify it worked with:

  ```
  uv --version
  ```

  **Still says `uv` is not recognized after reopening a terminal?** On Windows, a new *tab* or *window* in Windows Terminal / VS Code doesn't always pick up a PATH change — the terminal *application* itself needs to fully restart, since it re-reads the environment only when its own process starts. Try, in order:
  1. Fully quit the terminal app (not just the tab/window — e.g. quit Windows Terminal from the taskbar, or fully close and reopen VS Code), then relaunch it.
  2. If that still fails, log off and back on to Windows (or restart), which refreshes the environment for all new processes.
  3. To unblock yourself immediately without restarting anything, add it to just the current session:
     ```powershell
     $env:Path += ";$env:USERPROFILE\.local\bin"
     ```

  See the [official install docs](https://docs.astral.sh/uv/getting-started/installation/) for other options (e.g. `pip install uv`, Homebrew, winget).
- Node.js (only for running the static frontend's dev tooling/tests, if desired)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd LibSync
```

### 2. Configure the backend

Create a `.env` file inside `server/` (see `server/.env.example`):

```
HUGGINGFACE_TOKEN=your_huggingface_api_token_here
PINECONE_API_KEY=your_pinecone_api_key_here
PORT=3000
```

**Getting a Hugging Face token:** the Inference Providers API (used here to call `deepseek-ai/DeepSeek-V3.2-Exp` via novita) requires a token even on the free tier, since usage is tracked against your HF account.

1. Create a free account at [huggingface.co/join](https://huggingface.co/join).
2. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) and click **New token**.
3. A **Read** token is sufficient for inference calls — no billing setup required for free-tier model usage.
4. Copy the generated token into `HUGGINGFACE_TOKEN` in your `.env` file.

### 3. Install backend dependencies and run the server

`uv` reads `server/pyproject.toml`, creates an isolated virtual environment, and installs everything automatically — no manual `pip install` or `venv` activation required.

```bash
cd server
uv sync
uv run uvicorn app.main:app --reload --port 3000
```

The API is now running at `http://localhost:3000`, with interactive docs at `http://localhost:3000/docs`.

### 4. Run the backend tests

```bash
cd server
uv run pytest
```

### 5. Run the frontend locally

Open `client/src/index.html` in your browser. By default it points at the deployed Render backend — to test against your local server, update the `fetch` URL in `client/src/script.js`:

```JavaScript
const response = await fetch("http://localhost:3000/chat", { ... });
```

### 6. Start chatting! 💬

---

## 🗂️ Project Structure

```
LibSync/
├── client/src/          # Static frontend (vanilla JS/HTML/CSS)
├── docs/                # GitHub Pages mirror of client/src
├── server/              # Python/FastAPI + PydanticAI backend (uv-managed)
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, rate limiting, routers
│   │   ├── agent.py         # PydanticAI agent + system prompt
│   │   ├── bot_context/     # Persona and library-policy knowledge sources
│   │   ├── routers/         # /chat and /api/query endpoints
│   │   └── services/        # Pinecone client wrapper
│   ├── tests/            # pytest suite
│   └── pyproject.toml
└── pinecone-scripts/     # Python IaC scripts (uv-managed) for the Pinecone index
```

---

## ☁️ Cloud Deployment (Render)

- **Start Command:** `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory:** `server`
- **Environment Variables:** Set `HUGGINGFACE_TOKEN` and `PINECONE_API_KEY` on Render

Once deployed, update the frontend `fetch` URL to point to your Render URL:

```JavaScript
const response = await fetch("https://<your-render-app>.onrender.com/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message: question }),
});
```
---

## 🛠️ Next Steps

- **Model refinement:** Narrow AI responses to library-specific queries and improve policy adherence through prompt and model tuning.
- **RAG wiring:** Feed Pinecone search results into the PydanticAI agent's context for retrieval-augmented answers.
- **Frontend improvements:** Enhanced UI/UX, loading indicators, error handling, and session persistence for a smoother chat experience.
- **Additional features:** Logging, authentication, and advanced security optimizations.
- **Deployment optimization:** Expand **CI/CD** pipelines for automated testing, vector updates, and production deployment.


---

## 🚀 Featured Deployment

Experience LibSync in action! Interact with the chatbot and explore the UI:

| Environment | Link |
|-------------|------|
| Prod | [🌐 Visit LibSync](https://johnniemaeb.github.io/LibSync/)|

Interact with the chatbot, explore the interface, and see the project in action.

> **Note:** This is a demo project running exclusively on free-tier services. The backend on Render may spin down after periods of inactivity, which can result in a delay of up to ~50 seconds for the AI to respond when waking from idle.
