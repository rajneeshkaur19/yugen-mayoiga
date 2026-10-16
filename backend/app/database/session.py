
from sqlalchemy.orm import sessionmaker

from backend.app.database.connection import engine


# Creates database sessions when the application needs them.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)
