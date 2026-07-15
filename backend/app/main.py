import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from . import crud
from .agent.graph import build_agent
from .database import Base, SessionLocal, engine, get_db
from .schemas import ChatRequest, ChatResponse, InteractionSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First HCP CRM - Log Interaction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/interaction/{session_id}", response_model=InteractionSchema)
def get_interaction(session_id: str, db: Session = Depends(get_db)):
    """Lets the frontend restore form state on page refresh."""
    row = crud.get_or_create_interaction(db, session_id)
    return row.to_dict()


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    agent = build_agent(request.session_id)

    lc_history = []
    for m in request.history[-10:]:
        if m.role == "user":
            lc_history.append(HumanMessage(content=m.content))
        else:
            lc_history.append(AIMessage(content=m.content))
    lc_history.append(HumanMessage(content=request.message))

    try:
        result = agent.invoke({"messages": lc_history})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=502, detail=f"AI assistant error: {exc}") from exc

    final_message = result["messages"][-1]
    reply_text = final_message.content if isinstance(final_message.content, str) else str(final_message.content)

    row = crud.get_or_create_interaction(db, request.session_id)
    return ChatResponse(reply=reply_text, interaction=row.to_dict())


@app.post("/api/reset/{session_id}", response_model=InteractionSchema)
def reset(session_id: str, db: Session = Depends(get_db)):
    """Starts a fresh interaction draft in the same session (used by the
    frontend's "New Interaction" button)."""
    row = crud.reset_interaction(db, session_id)
    return row.to_dict()