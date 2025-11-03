import os
import uuid
import pika
import shutil
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy import create_engine, Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from contextlib import contextmanager

# --- 1. Konfiguracja Bazy Danych i SQLAlchemy ---

# Pobierz URL bazy z zmiennej środowiskowej (ustawionej w docker-compose)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres/db")

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Definicja modelu "Job" (nasz 'kontrakt' danych)
class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, default="PENDING", index=True)
    input_file_path = Column(String, nullable=True) # Ścieżka do pliku w wolumenie
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    result = Column(JSON, nullable=True)

# Funkcja pomocnicza do pobierania sesji DB w endpointach
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 2. Konfiguracja RabbitMQ ---

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
JOB_QUEUE = "job_queue" # Nazwa naszej kolejki

# --- 3. Inicjalizacja Aplikacji FastAPI ---

app = FastAPI(title="Upload Service")

@app.on_event("startup")
def on_startup():
    # Funkcja uruchamiana przy starcie serwera
    # Czeka, aż baza danych będzie gotowa i tworzy tabelę 'jobs'
    # (W prawdziwej produkcji użylibyśmy np. Alembic do migracji)
    import time
    time.sleep(5) # Daj postgresowi chwilę na start
    Base.metadata.create_all(bind=engine)

# --- 4. Główny Endpoint ---

@app.post("/api/v1/upload", status_code=201)
async def create_upload_job(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Ten endpoint przyjmuje plik CSV, zapisuje go i tworzy zadanie.
    """
    # 1. Sprawdź, czy to CSV (prosta walidacja)
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV accepted.")

    # 2. Wygeneruj unikalne ID i ścieżkę zapisu
    job_id = uuid.uuid4()
    # Zapiszemy plik w udostępnionym wolumenie, aby worker miał do niego dostęp
    file_path = f"/app/shared/uploads/{job_id}_{file.filename}"
    
    # Upewnij się, że katalog /app/uploads istnieje
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 3. Zapisz plik na dysku (w wolumenie)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # 4. Utwórz wpis w bazie danych
    new_job = Job(id=job_id, status="PENDING", input_file_path=file_path)
    db.add(new_job)
    db.commit()

    # 5. Wyślij komunikat do RabbitMQ
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue=JOB_QUEUE, durable=True) # durable=True = kolejka przetrwa restart
        
        channel.basic_publish(
            exchange='',
            routing_key=JOB_QUEUE,
            body=str(job_id), # Wyślij samo ID zlecenia jako string
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
        connection.close()
    except Exception as e:
        # Jeśli RabbitMQ zawiedzie, oznacz zadanie jako FAILED
        db.rollback()
        db.query(Job).filter(Job.id == job_id).update({"status": "FAILED"})
        db.commit()
        raise HTTPException(status_code=500, detail=f"Could not queue job: {e}")

    # 6. Zwróć ID zadania do frontendu
    return {"job_id": str(job_id)}