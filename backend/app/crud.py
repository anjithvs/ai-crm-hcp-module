"""
Small data-access layer sitting between the LangGraph tools and the DB.

Keeping this separate from tools.py means the tools stay focused on
"what does this tool do in agent terms", while this file owns "how do we
read/write a row". The DB row *is* the single source of truth for the
current draft interaction in a session -- there's no separate in-memory
state to keep in sync.
"""
from sqlalchemy.orm import Session

from .models import Interaction

EDITABLE_FIELDS = {
    "hcp_name",
    "interaction_type",
    "date",
    "time",
    "attendees",
    "topics_discussed",
    "materials_shared",
    "samples_distributed",
    "sentiment",
    "outcomes",
    "follow_up_actions",
    "compliance_flag",
}


def get_or_create_interaction(db: Session, session_id: str) -> Interaction:
    row = db.query(Interaction).filter(Interaction.session_id == session_id).first()
    if row is None:
        row = Interaction(session_id=session_id, attendees=[], materials_shared=[], samples_distributed=[])
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def update_interaction(db: Session, session_id: str, **fields) -> Interaction:
    """Update only the fields explicitly passed (skips anything set to None),
    so partial updates (e.g. the Edit Interaction tool) never clobber
    existing data with blanks."""
    row = get_or_create_interaction(db, session_id)
    for key, value in fields.items():
        if key not in EDITABLE_FIELDS:
            continue
        if value is None:
            continue
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def mark_logged(db: Session, session_id: str) -> Interaction:
    row = get_or_create_interaction(db, session_id)
    row.logged = True
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def reset_interaction(db: Session, session_id: str) -> Interaction:
    """Used when the rep starts logging a brand new interaction in the
    same browser tab (new session_id is usually simpler, but this is a
    safety net)."""
    row = get_or_create_interaction(db, session_id)
    for key in EDITABLE_FIELDS:
        setattr(row, key, [] if key in ("attendees", "materials_shared", "samples_distributed") else None)
    row.logged = False
    db.add(row)
    db.commit()
    db.refresh(row)
    return row