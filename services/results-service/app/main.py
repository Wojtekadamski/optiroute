import os
import uuid
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from pydantic import BaseModel # Użyjemy Pydantic do zdefiniowania modelu odpowiedzi

# --- 1. Konfiguracja Bazy Danych (Identyczna) ---

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres/db")

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Definicja modelu "Job" (musi być identyczna)
class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, default="PENDING", index=True)
    input_file_path = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    result = Column(JSON, nullable=True)

# Funkcja pomocnicza do pobierania sesji DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 2. Modele Pydantic (Definicja odpowiedzi API) ---
# To dobra praktyka, aby FastAPI wiedziało, jak ma wyglądać JSON zwrotny

class JobStatusResponse(BaseModel):
   
    id: uuid.UUID 
    status: str
    result: dict | None = None # Wynik będzie słownikiem (JSON) lub None

    class Config:
        from_attributes = True

# --- 3. Inicjalizacja Aplikacji FastAPI ---

app = FastAPI(title="Results Service")

@app.on_event("startup")
def on_startup():
    # Czekamy, aż tabela 'jobs' zostanie utworzona przez upload-service
    import time
    time.sleep(5) 

# --- 4. Główny Endpoint ---

@app.get("/api/v1/results/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Ten endpoint sprawdza status zadania w bazie danych.
    """
    # 1. Znajdź zadanie w bazie
    job = db.query(Job).filter(Job.id == job_id).first()
    
    # 2. Jeśli nie ma zadania, zwróć błąd 404
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # 3. Jeśli jest, zwróć jego status i wynik
    # (Pydantic automatycznie konwertuje obiekt 'job' na JSON)
    return job