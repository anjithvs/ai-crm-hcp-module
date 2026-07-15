"""
Database connection setup.

Uses SQLAlchemy so the same code works with PostgreSQL or MySQL --
just change DATABASE_URL in your .env file. See README.md for how to
get a free hosted Postgres database in under 2 minutes (no local install
needed), which is the easiest path for this assignment.

Examples of valid DATABASE_URL values:
  PostgreSQL:  postgresql+psycopg2://user:password@host:5432/hcp_crm
  MySQL:       mysql+pymysql://user:password@host:3306/hcp_crm
"""
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy backend/.env.example to backend/.env "
        "and fill in your database connection string. See README.md."
    )

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it.
    Used for the request/response path, where there's only ever one
    caller at a time."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """A short-lived session for a single unit of work.

    This is what the LangGraph tools use (see agent/tools.py) instead of
    sharing one Session for the whole request. That matters because
    LangGraph's ToolNode executes multiple tool calls from the same model
    turn *concurrently* in a thread pool whenever the model asks for more
    than one tool at once (e.g. a rep describing several things in one
    message). A SQLAlchemy Session is not safe to use from more than one
    thread at the same time -- sharing a single Session across tools
    caused exactly that error ("concurrent operations are not
    permitted"). Giving each tool call its own session, opened and closed
    within that single function call, avoids the problem entirely.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()