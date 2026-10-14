from fastapi import Request, Depends, HTTPException, status
from typing import Generator
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from nexus.core.persistence.repository import NexusRepository
from nexus.core.persistence.models import Base
from nexus.core.runner.pipeline import DecisionPipeline
from nexus.core.runner.gemini_client import GeminiLLMClient

DATABASE_URL = os.environ.get("NEXUS_DATABASE_URL", "sqlite:///nexus.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_repository(db: Session = Depends(get_db)) -> NexusRepository:
    return NexusRepository(db)

def get_llm_client() -> GeminiLLMClient:
    api_key = os.environ.get("GEMINI_API_KEY", "dummy_key")
    return GeminiLLMClient()

def get_pipeline(
    repo: NexusRepository = Depends(get_repository),
    llm_client: GeminiLLMClient = Depends(get_llm_client)
) -> DecisionPipeline:
    return DecisionPipeline(repo, llm_client)

