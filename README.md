# AI-First CRM · HCP Module — Log Interaction Screen

An AI-first "Log HCP Interaction" screen for a pharmaceutical CRM. Field
reps never fill the form by hand — they describe the visit in plain
English to an AI Assistant, and a **LangGraph agent** extracts the
details, calls the right tool, and populates the form live.

## What it does

- **Left panel** — the interaction record (HCP name, date, sentiment,
  materials shared, samples distributed, outcomes, follow-ups…). Read-only
  by design: it can only be changed by the AI Assistant, never typed into
  directly.
- **Right panel** — a chat interface. The rep describes the visit in one
  message; the agent extracts structured data and fills the form. If the
  rep spots a mistake, they just tell the assistant what changed, and only
  those fields update.

Example, exactly like the two mandatory tools are meant to behave:

```
Rep:       Today I met with Dr. Smith and discussed product X efficiency.
           The sentiment was positive and I shared the brochures.
Assistant: ✅ Logged. HCP: Dr. Smith · Sentiment: Positive · Materials: Brochures

Rep:       Sorry, the name was actually Dr. John and the sentiment was negative.
Assistant: ✅ Updated — name is now Dr. John, sentiment is now Negative.
           Everything else is unchanged.
```

## Architecture

```
┌─────────────────────┐        HTTP/JSON        ┌──────────────────────────┐
│   React + Redux      │  ───────────────────▶  │   FastAPI                │
│   (frontend/)         │  ◀───────────────────  │   POST /api/chat          │
│                       │                         │                          │
│  ┌─────────────┐      │                         │  ┌────────────────────┐  │
│  │ Interaction  │◀────┼── setInteraction() ─────┼──│  LangGraph Agent    │  │
│  │ Form (left)  │      │                         │  │  (agent/graph.py)   │  │
│  └─────────────┘      │                         │  └─────────┬──────────┘  │
│  ┌─────────────┐      │                         │            │             │
│  │ AI Assistant │──────┼── sendChatMessage() ───▶│    ┌───────▼────────┐    │
│  │ Chat (right) │      │                         │    │ Groq LLM        │    │
│  └─────────────┘      │                         │    │ gemma2-9b-it    │    │
└─────────────────────┘                         │    │ (+ llama-3.3-70b │    │
                                                   │    │  fallback)      │    │
                                                   │    └───────┬────────┘    │
                                                   │            │ tool calls  │
                                                   │    ┌───────▼────────┐    │
                                                   │    │ 5 LangGraph      │    │
                                                   │    │ Tools           │    │
                                                   │    │ (agent/tools.py)│    │
                                                   │    └───────┬────────┘    │
                                                   │            │             │
                                                   │    ┌───────▼────────┐    │
                                                   │    │ PostgreSQL /    │    │
                                                   │    │ MySQL (via      │    │
                                                   │    │ SQLAlchemy)     │    │
                                                   │    └────────────────┘    │
                                                   └──────────────────────────┘
```

**The LangGraph graph itself** (`backend/app/agent/graph.py`) is a small
loop, not just a single LLM call:

```
START ──▶ agent ──(model made a tool call?)──▶ tools ──▶ agent ──▶ ... ──▶ END
                └──(plain text reply)───────────────────────────────────▶ END
```

`agent` is one Groq call with the 5 tools bound to it. If it returns a
tool call, LangGraph's `tools_condition` routes to the `tools` node
(a `ToolNode`, which actually executes the tool against the database),
then loops back to `agent` so the model can turn the tool's result into a
natural-language confirmation. If the model just replies with text, the
graph ends. This is what lets a single user message like *"today I met
Dr. Smith… shared the brochures"* result in a tool call **and** a
friendly confirmation message in one round trip.

## The LangGraph agent's role

The agent is the only thing allowed to write to the interaction record.
It reads the rep's free-text message (and recent chat history for
context), decides which of the 5 tools apply, extracts the right
arguments for each (this is the "entity extraction" — the LLM's
tool-calling is what turns "Dr. Smith" / "positive" / "brochures" into
structured `hcp_name` / `sentiment` / `materials_shared` fields), and
returns a short confirmation. It never modifies fields the rep didn't
mention, which is what makes the Edit Interaction tool safe to use
repeatedly through a conversation.

## The 5 tools

| # | Tool | What it does |
|---|------|---------------|
| 1 | `log_interaction` **(mandatory)** | Parses a free-text description of a new visit and creates the interaction record — HCP name, date, sentiment, topics, materials, etc. |
| 2 | `edit_interaction` **(mandatory)** | Updates only the fields the rep explicitly corrects, leaving everything else untouched. |
| 3 | `suggest_follow_up` | Proposes a next-step action based on the logged sentiment (e.g. schedule a meeting for a positive interaction, escalate to MSL for a negative one) and records it. |
| 4 | `search_add_material` | Matches a material the rep mentions (e.g. "the dosing guide") against an approved materials catalog and attaches it. |
| 5 | `log_sample_distribution` | Records samples handed out and flags it if the quantity exceeds a per-visit compliance limit — a real constraint in regulated pharma sales (e.g. under the US PDMA). |

See the docstring on each tool in `backend/app/agent/tools.py` for the
exact arguments the model can use.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Redux Toolkit, Vite, plain CSS (Google Inter font) |
| Backend | Python, FastAPI |
| Agent framework | LangGraph (explicit `StateGraph`, not just the prebuilt helper) |
| LLM | Groq — `gemma2-9b-it` primary, `llama-3.3-70b-versatile` automatic fallback |
| Database | PostgreSQL or MySQL via SQLAlchemy |

## Project structure

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py       # LangGraph StateGraph wiring
│   │   │   └── tools.py       # the 5 tools
│   │   ├── main.py            # FastAPI app + routes
│   │   ├── database.py        # SQLAlchemy engine/session
│   │   ├── models.py          # Interaction table
│   │   ├── crud.py            # DB read/write helpers used by the tools
│   │   └── schemas.py         # Pydantic request/response models
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InteractionForm.jsx   # left panel
│   │   │   └── AIAssistantChat.jsx   # right panel
│   │   ├── store/                    # Redux slices
│   │   ├── api.js
│   │   └── App.jsx
│   └── package.json
├── SETUP_GUIDE.md       # zero-experience, step-by-step (Windows)
├── VIDEO_SCRIPT.md      # walkthrough script for the demo recording
└── README.md            # this file
```

## Quick start (if you already have Node, Python, Git, and a Postgres DB)

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows; use `source venv/bin/activate` on Mac/Linux
pip install -r requirements.txt
copy .env.example .env         # then fill in GROQ_API_KEY and DATABASE_URL
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 — the Vite dev server proxies `/api/*`
to the backend on port 8000.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/interaction/{session_id}` | Fetch (or create) the current draft for a session — used to restore state on refresh. |
| `POST` | `/api/chat` | Send a chat message; returns the assistant's reply and the updated interaction record. |
| `POST` | `/api/reset/{session_id}` | Clear the current draft to start logging a new interaction. |
| `GET` | `/api/health` | Basic health check. |

## Ideas for extending this

- Move `APPROVED_MATERIALS` / `SAMPLE_LIMITS` in `tools.py` into their own
  DB tables so they're editable without a code change.
- Add a `users` table and tie `session_id` to a logged-in rep instead of
  a browser session.
- Add a `checkpointer` to the LangGraph graph (LangGraph supports this
  natively) for true multi-turn memory across page reloads, instead of
  replaying recent chat history on every request.
- Voice-note summarization (there's a placeholder for it in the original
  mockup) would be a 6th tool: transcribe audio, then feed the transcript
  through the same extraction path as `log_interaction`.
