# Company Knowledge GraphRAG Chatbot

A multi-user chatbot that answers questions about a company's **employees, projects,
skills, and technologies**. It combines a **Neo4j knowledge graph** with **Claude**
(used through the Claude Code CLI) in a small **LangGraph agent**, served by a FastAPI
backend with a plain HTML/JS frontend.

The chatbot is *grounded*: instead of letting the LLM guess, the app first retrieves
real facts from the graph and feeds them to Claude — this is the core idea of
**GraphRAG** (Retrieval-Augmented Generation over a graph).

---

## Architecture

```
Browser (HTML/JS)
      │  POST /chat  { username, message, session_id }
      ▼
FastAPI  (app/api/chat.py)
      │  save user message → run_agent() → save reply
      ▼
LangGraph Agent  (app/agent/agent.py)
      │
      ├─ route    → Claude picks a tool        (claude_service.ask_claude)
      ├─ run_tool → calculator / graph_lookup / knowledge_search  (app/services/tools.py)
      │                │
      │                └─ graph tools query Neo4j  (app/services/graph_service.py)
      └─ respond  → Claude writes the final answer from the tool result
      ▼
Response  { reply, trace }   ← trace shows which tool ran (debug panel in UI)
```

Two data stores:

- **SQLite** (`database/chat.db`) — users, chat sessions, message history.
- **Neo4j** (Docker) — the company knowledge graph.

---

## How the LLM is used

This project does **not** use the Anthropic API or any Python SDK. Instead it calls
the **Claude Code CLI as a subprocess** — so there is no API key in the code; auth is
handled by the already-logged-in `claude` CLI.

### The single entry point — `ask_claude()`

`app/services/claude_service.py` builds a command list (never a shell string, to avoid
injection) and runs it:

```bash
claude -p "<prompt>" --output-format json --permission-mode dontAsk --tools "" --model claude-sonnet-4-6
```

- `--output-format json` → Claude replies as JSON; we parse `result` (the text) and
  `session_id` (to continue the conversation later).
- `--tools ""` → disables the CLI's own tools so Claude only answers.
- `--resume <session_id>` is added when continuing an existing conversation.
- `--system-prompt <...>` injects the assistant's persona from `prompts/chatbot_prompt.txt`.
- Errors are handled in exactly three places: non-zero exit, timeout, and bad JSON —
  each raises a clean `ClaudeError`.

The model and timeout come from `.env` (`CLAUDE_MODEL`, `CLAUDE_TIMEOUT`).

### The agent loop (LangGraph)

`app/agent/agent.py` defines a tiny state machine over `AgentState`:

1. **`route`** — asks Claude to reply with only a JSON object choosing one tool
   (`calculator`, `graph_lookup`, `knowledge_search`, or `none`) plus its input.
2. **`run_tool`** — runs the chosen tool with that input (skipped if `none`).
3. **`respond`** — asks Claude to write the final answer, given the tool result.

So a typical answer uses **two Claude calls** (route + respond). The graph is built with
`StateGraph`, compiled once into a module-level `agent_app`, and exposed via
`run_agent(question, session_id) -> (answer, trace)`. The `trace` records the tool, its
input, and result, which the frontend shows in a collapsible **🔍 Debug** panel.

---

## How the knowledge graph is created

### 1. The data — `data/knowledge_base.json`

The graph is described in one JSON file with two arrays:

```json
{
  "nodes": [
    { "id": "Ali Khan", "label": "Person", "properties": { "name": "Ali Khan", "role": "Senior AI Engineer" } },
    { "id": "Python",   "label": "Technology", "properties": { "name": "Python" } }
  ],
  "relationships": [
    { "from": "Ali Khan", "type": "WORKS_ON", "to": "Internal AI Assistant" },
    { "from": "Internal AI Assistant", "type": "USES", "to": "Python" }
  ]
}
```

- **Node labels:** `Person`, `Project`, `Skill`, `Technology`, `Company`.
- **Relationship types:** `KNOWS` (person→skill), `WORKS_ON` (person→project),
  `REPORTS_TO` (person→person), `USES` (project→technology),
  `WORKS_AT` (person→company), `MEMBER_OF` (person→department).
- Each `id` is a unique name, so the same thing (e.g. Python) is one shared node.

### 2. Loading into Neo4j — `scripts/load_graph.py`

`load_knowledge_base()` in `app/services/graph_service.py` reads the JSON and writes it
to Neo4j with **parameterized** Cypher:

```cypher
MERGE (n:Label {id: $id}) SET n += $props                       -- one per node
MATCH (a {id: $from}), (b {id: $to}) MERGE (a)-[:TYPE]->(b)     -- one per relationship
```

- **`MERGE`** means running the loader twice does not create duplicates (idempotent).
- Labels and relationship types **cannot** be passed as Cypher parameters, so they are
  validated against a small whitelist (`ALLOWED_LABELS`, `ALLOWED_REL_TYPES`) before use
  — this prevents injection while still being dynamic.

Run it:

```bash
PYTHONPATH=. uv run python scripts/load_graph.py
# -> Graph loaded: 27 nodes, 50 relationships
```

### 3. Retrieving facts (the "RAG" part)

When a question comes in, the graph tools turn it into grounded facts:

1. **`find_entities(question)`** — fetches all node ids and keeps the ones whose name
   appears in the question (simple case-insensitive substring match, no embeddings).
2. **`get_neighborhood(ids)`** — pulls each matched entity's 1-hop relationships.
3. **`retrieve_context(question)`** — turns those into readable lines and returns:

   ```
   Facts from the company knowledge graph:
   - Ali Khan WORKS_ON Internal AI Assistant
   - Ali Khan KNOWS Machine Learning
   ```

These facts are passed to Claude in `respond`, so the answer is based on the graph —
not on the model's imagination.

---

## Project structure

```
app/
  main.py                 FastAPI app, startup DB init, static frontend mount
  api/chat.py             POST /chat, GET /history/{id}
  agent/agent.py          LangGraph agent: AgentState + route/run_tool/respond
  models/
    db.py                 SQLite helpers (users, sessions, messages)
    schemas.py            Pydantic request/response models
  services/
    claude_service.py     ask_claude() — Claude Code CLI subprocess wrapper
    graph_service.py      Neo4j driver + load + GraphRAG retrieval
    tools.py              LangChain tools: calculator, graph_lookup, knowledge_search
data/knowledge_base.json  the graph definition
database/schema.sql       SQLite schema
scripts/load_graph.py     load the JSON into Neo4j
prompts/chatbot_prompt.txt the assistant's system prompt
frontend/                 index.html, style.css, app.js (vanilla, no framework)
docker-compose.yml        Neo4j (community) container
show_db.sh / delete_db.sh helpers to inspect / reset the SQLite data
```

---

## Setup & run

**Requirements:** Python 3.10+, [uv](https://docs.astral.sh/uv/), Docker, and the
`claude` CLI (logged in).

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env        # then edit NEO4J_PASSWORD etc.

# 3. Start Neo4j
docker compose up -d        # Neo4j browser at http://localhost:7474

# 4. Load the knowledge graph
PYTHONPATH=. uv run python scripts/load_graph.py

# 5. Run the app
PYTHONPATH=. uv run uvicorn app.main:app --reload
```

Open **http://localhost:8000** for the chat UI, or **/docs** for the Swagger API.

---

## API

| Method | Path                 | Body / Params                          | Returns                          |
|--------|----------------------|----------------------------------------|----------------------------------|
| POST   | `/chat`              | `{ username, message, session_id? }`   | `{ session_id, reply, trace }`   |
| GET    | `/history/{id}`      | session id in path                     | `[ { role, content } ]`          |
| GET    | `/health`            | —                                      | `{ status: "ok" }`               |

`session_id` is `null` for a new conversation; the returned id is reused for follow-ups.

---

## Helper scripts

```bash
./show_db.sh              # users, sessions, message counts
./show_db.sh 3            # full chat history for session 3
./delete_db.sh all        # wipe all data and reset ids to 1
```

---

## Environment variables

| Variable          | Default                | Purpose                              |
|-------------------|------------------------|--------------------------------------|
| `CLAUDE_MODEL`    | `claude-sonnet-4-6`    | Model for chat answers and routing   |
| `CLAUDE_TIMEOUT`  | `120`                  | CLI call timeout (seconds)           |
| `ROUTING_MODEL`   | `claude-sonnet-4-6`    | Model for the agent's router node    |
| `NEO4J_URI`       | `bolt://localhost:7687`| Neo4j Bolt connection                |
| `NEO4J_USER`      | `neo4j`                | Neo4j username                       |
| `NEO4J_PASSWORD`  | —                      | Neo4j password (keep in `.env` only) |

> `.env` is git-ignored and never committed — only `.env.example` (with placeholder
> values) is in the repo.
