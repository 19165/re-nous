# 🌸 Multi-Agent Research Assistant (v1.0.0)

An enterprise-grade, autonomous **Multi-Agent Research Assistant** built with **Python**, **LangGraph**, **Ollama** (Local LLM), **Tavily API**, **Redis**, **PostgreSQL**, and **FastAPI**. 

The system takes a complex research question, breaks it down into sub-tasks, performs concurrent web searches, evaluates quality through a Supervisor agent, validates all citations, and synthesizes a fully verified research report with step-level audit tracing.

---

## 🏗️ Production Architecture

The system is architected around a **Two-Tier Storage Layer** coupled with a **State Machine Orchestrator**:

```mermaid
graph TD
    User([User / Client]) -->|HTTP / SSE| API[FastAPI Web Service]
    
    subgraph Tier 1: In-Flight & Real-time Layer [⚡ Redis]
        Cache[24h Deterministic Node Cache SHA-256]
        PubSub[Real-time Event Stream Pub/Sub]
        Checkpoints[LangGraph In-Flight Checkpointing]
    end

    subgraph Multi-Agent State Machine [🤖 LangGraph Orchestrator]
        Planner[🧭 Planning Agent] -->|Map: Sub-questions| Researchers[🔍 Research Agents]
        Researchers --> Supervisor[🛡️ Supervisor QA & Budget Gatekeeper]
        Supervisor -.->|Needs Revision & Count == 0| Researchers
        Supervisor -->|Approved OR Budget Reached| Validator[🔍 Citation Validation Engine]
        Validator --> Writer[📝 Writer Agent]
    end

    subgraph Tier 2: Permanent Storage Layer [🐘 PostgreSQL 18]
        Runs[(research_runs Table: Reports, Tokens, Status)]
        Traces[(trace_steps Table: Full Audit Trail & Latency)]
    end

    API --> Multi-Agent State Machine
    Multi-Agent State Machine <--> Tier 1
    Multi-Agent State Machine --> Tier 2
```

---

## 🌟 Key Features

1. **Map-Reduce Orchestration**: LangGraph StateGraph with async parallel workers (`Send` API) and structured aggregation.
2. **Supervisor Quality Assurance**: Evaluates findings, checks source adequacy, and enforces an exact-once revision loop.
3. **Hard Budget Enforcement**: Protects compute/search spend via wall-clock timeouts, token ceilings, search limits, and per-domain capping.
4. **Deterministic Node Caching (Redis)**: 24-hour SHA-256 caching for agent node outputs (0 tokens, 0ms latency on repeated queries).
5. **Permanent Step-Level Tracing (PostgreSQL)**: Full audit trail of every agent action (input payload, output payload, tools called, token usage, and latency).
6. **Citation Validation Engine**: Programmatically verifies all inline references (`[1]`, `[2]`) against actual retrieved search sources to prevent hallucinations.
7. **FastAPI REST API & SSE Streaming**: Asynchronous execution (`POST /research`) with real-time Server-Sent Events (`GET /research/{id}?stream=true`).

---

## 📂 Project Structure

```text
.
├── agents/
│   ├── base_agent.py             # Base agent interface
│   ├── planning_agent.py         # Sub-question decomposition agent
│   ├── research_agent.py         # Async web researcher (Tavily search + query optimizer)
│   ├── supervisor_agent.py       # Quality assurance evaluator & budget gatekeeper
│   └── writer_agent.py           # Structured report synthesizer
├── api/
│   ├── app.py                    # FastAPI application & lifespan setup
│   ├── routes.py                 # REST route handlers (/research, /research/{id}, /trace)
│   └── sse.py                    # Server-Sent Events (SSE) streaming via Redis Pub/Sub
├── db/
│   ├── database.py               # Async SQLAlchemy engine & session factory
│   └── models.py                 # ResearchRun & TraceStep models
├── orchestrators/
│   └── research_orchestrator.py  # Main LangGraph StateGraph workflow with Supervisor & Tracing
├── services/
│   ├── run_manager.py            # PostgreSQL ResearchRun persistence manager
│   └── tracer.py                 # Step-level audit tracer & SSE event publisher
├── tools/
│   ├── base_tool.py              # Base tool interface
│   └── search_tool.py            # Tavily search tool adapter
├── utils/
│   ├── citation_validator.py     # Inline citation verification against search findings
│   ├── logger.py                 # Rich logger & colorized console panels
│   ├── redis_cache.py            # Deterministic SHA-256 node caching utility
│   └── helpers.py                # Pydantic parsing & token counting helpers
├── tests/
│   ├── test_agents.py            # Unit tests for individual agents
│   ├── test_orchestrator.py      # Integration tests for StateGraph compilation
│   └── test_api.py               # Endpoint tests for FastAPI & Citation Validator
├── config.py                     # Environment & model configurations
├── docker-compose.yml            # Docker setup for Redis + PostgreSQL 18
├── main.py                       # CLI & Web Server entry point
├── pyproject.toml                # Project metadata & dependencies
├── requirements.txt              # Production dependencies
└── .env.example                  # Environment configuration template
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.12+
- Docker & Docker Compose
- [Ollama](https://ollama.ai/) running locally with your desired model (e.g., `ollama run llama3` or `gemma4:31b`)
- [Tavily API Key](https://tavily.com/)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/AI-AGENT.git
cd AI-AGENT

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file from the template:
```bash
cp .env.example .env
```
Edit `.env` and set your `TAVILY_API_KEY`:
```ini
TAVILY_API_KEY=tvly-your-api-key-here
```

### 4. Start Infrastructure (Redis & PostgreSQL)
```bash
docker compose up -d
```

---

## 💻 Usage

### Mode A: Run via FastAPI REST API (Recommended)
Start the web server:
```bash
python main.py --serve --port 8000
```
Visit the interactive Swagger UI documentation at: **`http://localhost:8000/docs`**

#### 1. Submit a Research Question
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"question": "How do Transformer models process self-attention?"}'
```
*Response (HTTP 202 Accepted):*
```json
{
  "run_id": "run-a1b2c3d4",
  "status": "PENDING",
  "message": "Research job submitted successfully. Track status or stream progress using this run_id."
}
```

#### 2. Stream Real-time Progress (SSE)
```bash
curl -N http://localhost:8000/research/run-a1b2c3d4?stream=true
```

#### 3. Retrieve Completed Report
```bash
curl http://localhost:8000/research/run-a1b2c3d4
```

#### 4. Retrieve Step-by-Step Audit Trace
```bash
curl http://localhost:8000/research/run-a1b2c3d4/trace
```

---

### Mode B: Run via Command Line Interface (CLI)
```bash
python main.py --query "Impact of Quantum Computing on Modern Cryptography" --timeout 60 --max-sub-questions 3
```

---

## 🧪 Running Tests

```bash
# 1. Test FastAPI Endpoints & Citation Validator
python tests/test_api.py

# 2. Test StateGraph Compilation
python tests/test_orchestrator.py

# 3. Test Individual Specialist Agents
python tests/test_agents.py --agent all
```

---

## 📄 License
MIT License.
