"""
The LangGraph agent that powers the AI Assistant panel.

Graph shape:

    START -> agent -> (conditional) -> tools -> agent -> ... -> END
                    -> (no tool call) -> END

`agent` is a single LLM call (Groq's gemma2-9b-it, with an automatic
fallback to llama-3.3-70b-versatile if the primary call errors) with the
5 tools bound to it. `tools` is LangGraph's prebuilt ToolNode, which
actually executes whichever tool(s) the model decided to call and feeds
the result back to `agent`. `tools_condition` is what makes this a *loop*
rather than a single call: after the model responds, LangGraph checks
whether that response contains a tool call. If yes, route to `tools` and
come back to `agent` so it can turn the tool's result into a reply. If
no, the model produced a plain-text reply, and the graph ends.

This manual graph (rather than `langgraph.prebuilt.create_react_agent`)
is a few more lines, but it's what actually makes this a *LangGraph
agent* in the sense the assignment is testing: explicit state, nodes and
edges the graph is built from, that we can reason about and extend.
"""
import logging
import os
from datetime import date
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .tools import build_tools

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "gemma2-9b-it"
FALLBACK_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are the AI Assistant embedded in a pharmaceutical CRM's \
"Log HCP Interaction" screen, used by field representatives to record their \
visits with Healthcare Professionals (HCPs).

Today's date is {today}.

Rules:
- You must use the provided tools to make any change to the interaction \
record. Never just describe what you would fill in -- actually call the tool.
- If nothing has been logged yet in this conversation, the rep's first \
description of a visit should be captured with log_interaction.
- If the rep is correcting or adding to something already logged, use \
edit_interaction and pass ONLY the fields that changed.
- Sentiment must always be exactly "Positive", "Neutral", or "Negative".
- If the rep mentions a follow-up need, or after logging seems like a \
natural moment to propose one, use suggest_follow_up.
- If the rep mentions sharing a specific material by name, use \
search_add_material so it's matched against the approved catalog.
- If the rep mentions handing out samples, use log_sample_distribution.
- After a tool call finishes, reply in one short, warm confirmation \
sentence summarizing what was captured or changed. If a tool result \
contains a compliance_flag, always surface it to the rep clearly.
"""


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def _make_llm(model_name: str) -> ChatGroq:
    return ChatGroq(
        model_name=model_name,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )


def build_agent(session_id: str):
    """Compiles a fresh graph for this request, with tools bound to this
    session_id via closures in build_tools. Each tool manages its own DB
    session internally (see tools.py) so concurrent tool calls within a
    single turn are safe."""
    tools = build_tools(session_id)

    primary_llm = _make_llm(PRIMARY_MODEL).bind_tools(tools)
    fallback_llm = _make_llm(FALLBACK_MODEL).bind_tools(tools)

    system_message = SystemMessage(content=SYSTEM_PROMPT.format(today=date.today().isoformat()))

    def agent_node(state: AgentState):
        messages = [system_message] + state["messages"]
        try:
            response = primary_llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - genuinely want to catch any Groq/API error here
            logger.warning("Primary model %s failed (%s); falling back to %s", PRIMARY_MODEL, exc, FALLBACK_MODEL)
            response = fallback_llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()