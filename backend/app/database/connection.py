import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine


# Resolve the backend directory independently of the terminal's location.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

# Load environment variables from backend/.env.
load_dotenv(ENV_FILE)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        f"DATABASE_URL is missing. Add it to {ENV_FILE}"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)
