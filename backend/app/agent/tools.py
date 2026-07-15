"""
The 5 LangGraph tools for the HCP Log Interaction agent.

Each tool is built by `build_tools(session_id)`, which closes over the
current session_id. That's what lets a tool like `edit_interaction` update
"the form the rep is currently looking at" without the LLM ever having to
know or pass around a session id itself -- the model only ever sees the
fields it needs to extract from natural language.

Each tool opens and closes its OWN short-lived DB session (via
`database.session_scope`) rather than sharing one across the whole agent
run. This matters: when a rep's message covers more than one action
(e.g. "suggest a follow-up, I gave them the dosing guide, and 10 samples"),
Groq's model returns multiple tool calls in a single turn, and LangGraph's
ToolNode executes them *concurrently* in a thread pool. A single shared
SQLAlchemy Session cannot safely be used from more than one thread at
once -- sharing one caused an "concurrent operations are not permitted"
error in practice. Giving each tool its own session avoids that entirely.

Tool 1: log_interaction        (mandatory)
Tool 2: edit_interaction       (mandatory)
Tool 3: suggest_follow_up      -- proposes (and records) a next-step action
Tool 4: search_add_material    -- looks up approved marketing materials and attaches them
Tool 5: log_sample_distribution -- records samples given out, with a basic compliance check
"""
import difflib
from datetime import date, timedelta
from typing import List, Optional

from langchain_core.tools import tool

from .. import crud
from ..database import session_scope

APPROVED_MATERIALS = [
    "Brochures",
    "Clinical Study Reprint - Efficacy Data",
    "Dosing & Administration Guide",
    "Patient Savings Card",
    "Leave-Behind: Safety Summary",
    "Product Sample Kit Overview",
]

SAMPLE_LIMITS = {
    "Prodo-X 10mg Sample": 4,
    "Prodo-X 20mg Sample": 2,
    "Prodo-X Starter Pack": 1,
}


def _resolve_date(text: Optional[str]) -> Optional[str]:
    """Turns relative phrases the LLM might pass through into ISO dates.
    The LLM is instructed to pass dates through as-is (e.g. "today",
    "yesterday", or an explicit date); we normalize here so the tool's
    behavior doesn't depend on the LLM getting formatting exactly right."""
    if not text:
        return None
    normalized = text.strip().lower()
    if normalized == "today":
        return date.today().isoformat()
    if normalized == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    return text.strip()


def _closest_match(query: str, options: List[str], cutoff: float = 0.4) -> Optional[str]:
    matches = difflib.get_close_matches(query.lower(), [o.lower() for o in options], n=1, cutoff=cutoff)
    if not matches:
        return None
    idx = [o.lower() for o in options].index(matches[0])
    return options[idx]


def build_tools(session_id: str):
    """Returns the 5 tools, each bound to this request's session_id. Each
    tool opens its own DB session internally -- see module docstring."""

    @tool
    def log_interaction(
        hcp_name: str,
        interaction_type: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        topics_discussed: Optional[str] = None,
        materials_shared: Optional[List[str]] = None,
        sentiment: Optional[str] = None,
        outcomes: Optional[str] = None,
    ) -> dict:
        """Log a brand-new HCP interaction from a free-text description.

        Use this the FIRST time in a conversation that the rep describes an
        interaction (e.g. "Today I met with Dr. Smith and discussed Prodo-X
        efficacy, sentiment was positive, I shared the brochures"). Extract
        every field you can find evidence for in the text; leave anything
        not mentioned as null rather than guessing.

        Args:
            hcp_name: Full name of the healthcare professional, e.g. "Dr. Smith".
            interaction_type: One of "Meeting", "Call", "Email", "Conference". Defaults to "Meeting".
            date: The date of the interaction. Pass through phrases like "today"/"yesterday" or an explicit date as written.
            time: The time of the interaction, if mentioned.
            attendees: Names of any other attendees mentioned besides the HCP.
            topics_discussed: A short summary of what was discussed.
            materials_shared: Any brochures, leave-behinds, or materials mentioned as shared.
            sentiment: The HCP's reaction -- must be exactly "Positive", "Neutral", or "Negative".
            outcomes: Any agreements or outcomes mentioned.
        """
        with session_scope() as db:
            crud.update_interaction(
                db,
                session_id,
                hcp_name=hcp_name,
                interaction_type=interaction_type or "Meeting",
                date=_resolve_date(date) or _resolve_date("today"),
                time=time,
                attendees=attendees,
                topics_discussed=topics_discussed,
                materials_shared=materials_shared,
                sentiment=sentiment,
                outcomes=outcomes,
            )
            row = crud.mark_logged(db, session_id)
            return {"status": "logged", "interaction": row.to_dict()}

    @tool
    def edit_interaction(
        hcp_name: Optional[str] = None,
        interaction_type: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        topics_discussed: Optional[str] = None,
        materials_shared: Optional[List[str]] = None,
        sentiment: Optional[str] = None,
        outcomes: Optional[str] = None,
    ) -> dict:
        """Correct or change specific fields of the interaction ALREADY logged
        in this session (e.g. "sorry, the name was actually Dr. John and the
        sentiment was negative").

        Only pass the fields the rep is actually correcting -- leave every
        other argument null so it does not overwrite existing data. Never
        call this before log_interaction has been called at least once in
        the conversation.

        Args: same meaning as in log_interaction, all optional -- pass only
        what changed.
        """
        with session_scope() as db:
            existing = crud.get_or_create_interaction(db, session_id)
            if not existing.logged:
                return {
                    "status": "error",
                    "message": "Nothing has been logged yet in this session, so there is nothing to edit. Use log_interaction first.",
                }
            row = crud.update_interaction(
                db,
                session_id,
                hcp_name=hcp_name,
                interaction_type=interaction_type,
                date=_resolve_date(date),
                time=time,
                attendees=attendees,
                topics_discussed=topics_discussed,
                materials_shared=materials_shared,
                sentiment=sentiment,
                outcomes=outcomes,
            )
            return {"status": "updated", "interaction": row.to_dict()}

    @tool
    def suggest_follow_up(reason: Optional[str] = None) -> dict:
        """Propose a next-step follow-up action for this HCP based on the
        logged sentiment, and record it in the interaction's follow-up field.

        Call this when the rep asks for a follow-up suggestion, or after
        logging an interaction if it seems like a natural next step.

        Args:
            reason: Optional extra context from the rep about what kind of follow-up they want.
        """
        with session_scope() as db:
            row = crud.get_or_create_interaction(db, session_id)
            sentiment = (row.sentiment or "Neutral").lower()
            if reason:
                suggestion = reason.strip()
            elif sentiment == "positive":
                suggestion = "Schedule an in-person follow-up meeting in 2 weeks to discuss adoption."
            elif sentiment == "negative":
                suggestion = "Escalate to the Medical Science Liaison for a detailed follow-up before the next visit."
            else:
                suggestion = "Send additional clinical data by email within 1 week."

            updated = crud.update_interaction(db, session_id, follow_up_actions=suggestion)
            return {"status": "suggested", "follow_up_actions": suggestion, "interaction": updated.to_dict()}

    @tool
    def search_add_material(query: str) -> dict:
        """Search the approved marketing materials catalog and attach any
        matching item(s) to the interaction's "materials shared" list.

        Call this when the rep mentions sharing a specific material by name
        that doesn't exactly match what's already recorded (e.g. "I also
        gave them the dosing guide").

        Args:
            query: The material name or description as the rep described it.
        """
        match = _closest_match(query, APPROVED_MATERIALS)
        if not match:
            return {
                "status": "not_found",
                "message": f"No approved material matched '{query}'.",
                "available_materials": APPROVED_MATERIALS,
            }
        with session_scope() as db:
            row = crud.get_or_create_interaction(db, session_id)
            current = list(row.materials_shared or [])
            if match not in current:
                current.append(match)
            updated = crud.update_interaction(db, session_id, materials_shared=current)
            return {"status": "added", "material": match, "interaction": updated.to_dict()}

    @tool
    def log_sample_distribution(sample_name: str, quantity: int) -> dict:
        """Record pharmaceutical samples handed to the HCP during this
        interaction, and flag it if the quantity exceeds the per-visit
        compliance limit for that sample.

        Args:
            sample_name: Name of the sample product as the rep described it.
            quantity: Number of units distributed.
        """
        match = _closest_match(sample_name, list(SAMPLE_LIMITS.keys()), cutoff=0.3) or sample_name
        limit = SAMPLE_LIMITS.get(match)

        with session_scope() as db:
            row = crud.get_or_create_interaction(db, session_id)
            current = list(row.samples_distributed or [])
            current.append({"name": match, "quantity": quantity})

            compliance_flag = None
            if limit is not None and quantity > limit:
                compliance_flag = (
                    f"⚠ Compliance: {quantity} units of '{match}' logged, "
                    f"exceeding the {limit}-unit per-visit limit."
                )

            updated = crud.update_interaction(
                db,
                session_id,
                samples_distributed=current,
                compliance_flag=compliance_flag,
            )
            return {
                "status": "logged",
                "sample": match,
                "quantity": quantity,
                "compliance_flag": compliance_flag,
                "interaction": updated.to_dict(),
            }

    return [
        log_interaction,
        edit_interaction,
        suggest_follow_up,
        search_add_material,
        log_sample_distribution,
    ]