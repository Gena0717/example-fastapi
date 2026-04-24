from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import settings
import app.models  # noqa: F401

engine = create_engine(settings.database_url)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session 