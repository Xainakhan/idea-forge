"""FastAPI application for generating structured software-business ideas."""

import os
import sqlite3
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .generator import IdeaGenerator

load_dotenv()
DATA_DIR = Path(os.getenv("IDEALIST_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "idealist.db"

IDEA_FIELDS = {
    "title": "A short, memorable product name.",
    "problem": "The concrete business problem being solved.",
    "category": "The product category, such as POS, car website, automation, or SaaS.",
    "target_users": "Who would use or buy this product.",
    "core_features": "Three to five concise, practical features.",
    "suggested_stack": "A realistic technology stack for an MVP.",
    "why_now": "Why this is useful or differentiated today.",
}


class GenerateIdeaRequest(BaseModel):
    category: Optional[str] = Field(default=None, max_length=100)


class IdeaResponse(BaseModel):
    id: int
    title: str
    problem: str
    category: str
    target_users: str
    core_features: str
    suggested_stack: str
    why_now: str
    is_favorite: bool
    created_at: str
    generation_source: str


class FavoriteResponse(BaseModel):
    id: int
    is_favorite: bool


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                problem TEXT NOT NULL,
                category TEXT NOT NULL,
                target_users TEXT NOT NULL,
                core_features TEXT NOT NULL,
                suggested_stack TEXT NOT NULL,
                why_now TEXT NOT NULL,
                generation_source TEXT NOT NULL DEFAULT 'ai',
                is_favorite INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(ideas)")}
        if "generation_source" not in columns:
            connection.execute("ALTER TABLE ideas ADD COLUMN generation_source TEXT NOT NULL DEFAULT 'ai'")


def row_to_idea(row: sqlite3.Row) -> dict:
    idea = dict(row)
    idea["is_favorite"] = bool(idea["is_favorite"])
    return idea


def save_idea(idea: dict, generation_source: str = "ai") -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    fields = tuple(IDEA_FIELDS.keys())
    values = tuple(idea[field] for field in fields)
    with get_connection() as connection:
        cursor = connection.execute(
            f"INSERT INTO ideas ({', '.join(fields)}, created_at, generation_source) VALUES ({', '.join('?' for _ in fields)}, ?, ?)",
            (*values, created_at, generation_source),
        )
        row = connection.execute("SELECT * FROM ideas WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_idea(row)


def create_generator() -> IdeaGenerator:
    generator = IdeaGenerator(
        name="Idealist",
        description="Generate original, viable software and automation business ideas.",
        model=os.getenv("IDEALIST_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("IDEALIST_EMBEDDING_MODEL", "text-embedding-3-small"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_recent_ideas=int(os.getenv("IDEALIST_MAX_RECENT_IDEAS", "20")),
        enable_embeddings=os.getenv("IDEALIST_ENABLE_EMBEDDINGS", "true").lower() == "true",
        generator_id="idealist",
    )
    # The library normally writes beside the process. Keep API state contained
    # in a dedicated directory instead.
    generator.csv_filename = str(DATA_DIR / "ideas_idealist.csv")
    generator.setup_parameters(IDEA_FIELDS)
    return generator


def provider_configuration_error() -> Optional[str]:
    """Return a helpful setup error before attempting a paid provider request."""
    model = os.getenv("IDEALIST_MODEL", "gpt-4o-mini").lower()
    required_key = None
    if "openrouter" in model:
        required_key = "OPENROUTER_API_KEY"
    elif "gpt" in model or "openai" in model:
        required_key = "OPENAI_API_KEY"
    elif "gemini" in model:
        required_key = "GEMINI_API_KEY"
    elif "groq" in model:
        required_key = "GROQ_API_KEY"
    elif "anthropic" in model or "claude" in model:
        required_key = "ANTHROPIC_API_KEY"

    if required_key and not os.getenv(required_key):
        return f"{required_key} is not configured in the backend .env file."
    return None


def generate_fallback_idea(category: str) -> dict:
    """Generate a useful local idea when an AI provider is unavailable."""
    focus = category.strip().title() if category else "Business Operations"
    nouns = ("Flow", "Pilot", "Pulse", "Desk", "Bridge", "Loop", "Ledger", "Signal")
    jobs = ("follow-ups", "appointments", "quotes", "customer updates", "daily handoffs", "repeat orders")
    audiences = ("independent local businesses", "small service teams", "owner-operators", "growing agencies")
    with get_connection() as connection:
        existing_titles = {row[0].lower() for row in connection.execute("SELECT title FROM ideas")}

    seed = int(sha256(f"{category}|{len(existing_titles)}".encode()).hexdigest(), 16)
    for offset in range(len(nouns) * len(jobs)):
        noun = nouns[(seed + offset) % len(nouns)]
        job = jobs[((seed // len(nouns)) + offset) % len(jobs)]
        title = f"{focus.replace(' ', '')}{noun}"
        if offset:
            title = f"{title} {offset + 1}"
        if title.lower() not in existing_titles:
            return {
                "title": title,
                "problem": f"{audiences[seed % len(audiences)].capitalize()} lose time managing {job} across chats, calls, and spreadsheets.",
                "category": category or "business automation",
                "target_users": audiences[seed % len(audiences)],
                "core_features": f"A shared {job} board, automated reminders, simple status tracking, and weekly performance summaries.",
                "suggested_stack": "Next.js, FastAPI, SQLite, and a background job worker.",
                "why_now": f"{focus} teams need a low-cost way to standardize {job} without adopting a complex enterprise system.",
            }
    return generate_fallback_idea(f"{category} {len(existing_titles) + 1}")


generator = create_generator()
initialize_database()
app = FastAPI(title="Idealist API", version="0.1.0")

allowed_origins = [origin.strip() for origin in os.getenv(
    "CORS_ORIGINS", "http://localhost:3000"
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ideas/generate", response_model=IdeaResponse)
def generate_idea(request: GenerateIdeaRequest) -> dict:
    configuration_error = provider_configuration_error()
    category = request.category.strip() if request.category else "general software business"
    idea = None
    if not configuration_error:
        try:
            idea = generator.generate_idea(
                context=f"Focus the idea on this requested category: {category}."
            )
        except Exception:
            idea = None

    if idea:
        return save_idea(idea, generation_source="ai")
    return save_idea(generate_fallback_idea(category), generation_source="fallback")


@app.get("/ideas", response_model=list[IdeaResponse])
def list_ideas(favorites_only: bool = False) -> list[dict]:
    query = "SELECT * FROM ideas"
    if favorites_only:
        query += " WHERE is_favorite = 1"
    query += " ORDER BY id DESC"
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return [row_to_idea(row) for row in rows]


@app.patch("/ideas/{idea_id}/favorite", response_model=FavoriteResponse)
def toggle_favorite(idea_id: int) -> dict:
    with get_connection() as connection:
        row = connection.execute("SELECT is_favorite FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Idea not found.")
        is_favorite = not bool(row["is_favorite"])
        connection.execute("UPDATE ideas SET is_favorite = ? WHERE id = ?", (is_favorite, idea_id))
    return {"id": idea_id, "is_favorite": is_favorite}
