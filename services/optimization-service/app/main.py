import os
import uuid
import pika
import time
import csv
import json
from sqlalchemy import create_engine, Column, String, DateTime, JSON, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base # Importuj declarative_base

# NOWY IMPORT: Importujemy naszą nową funkcję
from geocoder import geocode_address 

# --- 1. Konfiguracja Bazy Danych (Bez zmian) ---

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://optiroute:optiroute123@postgres/optiroute")

Base = declarative_base() # Użyj declarative_base, którą importowałeś
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Model Job (Bez zmian)
class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, default="PENDING", index=True)
    # Ścieżka pliku musi pasować do konfiguracji docker-compose.yml
    input_file_path = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    result = Column(JSON, nullable=True)

# Funkcja pomocnicza do pobierania sesji DB (Bez zmian)
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass 

# --- 2. Konfiguracja RabbitMQ (Bez zmian) ---

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://optiroute:optiroute123@rabbitmq:5672/")
JOB_QUEUE = "job_queue"

# --- 3. Główna logika workera (TUTAJ ZMIANY) ---

def process_job(job_id):
    """
    Funkcja, która wykonuje całą logikę przetwarzania zlecenia.
    """
    db = get_db()
    try:
        print(f"[{job_id}] Rozpoczynam przetwarzanie...")
        
        # 1. Pobierz zadanie z bazy (Bez zmian)
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            print(f"[{job_id}] BŁĄD: Nie znaleziono zlecenia w bazie.")
            return

        # 2. Oznacz zadanie jako "PROCESSING" (Bez zmian)
        job.status = "PROCESSING"
        db.commit()

        # 3. Odczytaj plik CSV (Bez zmian)
        if not os.path.exists(job.input_file_path):
             raise FileNotFoundError(f"Plik {job.input_file_path} nie istnieje.")
        
        parsed_addresses = []
        with open(job.input_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # Zakładamy, że adres jest w pierwszej kolumnie
                if row: # Pomiń puste linie
                    parsed_addresses.append(row[0]) 
        
        print(f"[{job_id}] Znaleziono {len(parsed_addresses)} adresów w CSV.")

        # --- NOWA LOGIKA GEOKODOWANIA ---
        
        geocoded_results = []
        for address in parsed_addresses:
            print(f"[{job_id}] Geokodowanie adresu: {address}")
            coords = geocode_address(address)
            
            if coords:
                geocoded_results.append({
                    "address": address,
                    "lat": coords[0],
                    "lon": coords[1]
                })
            else:
                geocoded_results.append({
                    "address": address,
                    "error": "Nie znaleziono współrzędnych"
                })
            
            # WAŻNE: Polityka API Nominatim (max 1 zapytanie/sek)
            print(f"[{job_id}] Czekam 1 sekundę (polityka API Nominatim)...")
            time.sleep(1) 
        
        # ------------------------------------

        # 4. Zapisz wynik (teraz ze współrzędnymi)
        job.status = "COMPLETED"
        job.result = {
            "message": "Geokodowanie zakończone.",
            "processed_count": len(geocoded_results),
            "geocoded_stops": geocoded_results 
        }
        db.commit()
        print(f"[{job_id}] Zakończono pomyślnie. Zgeokodowano {len(geocoded_results)} adresów.")

    except Exception as e:
        # 5. Obsługa błędów (Bez zmian)
        print(f"[{job_id}] BŁĄD KRYTYCZNY: {e}")
        if db.is_active:
            db.rollback()
        
        # Sprawdź, czy 'job' istnieje, zanim spróbujesz go zaktualizować
        job_to_fail = db.query(Job).filter(Job.id == job_id).first()
        if job_to_fail:
            job_to_fail.status = "FAILED"
            job_to_fail.result = {"error": str(e)}
            db.commit()
    finally:
        db.close()

# Funkcja main() i reszta pliku pozostają BEZ ZMIAN
def main():
    # Czekaj na RabbitMQ i połącz się
    connection = None
    while not connection:
        try:
            # Używamy pika.URLParameters, aby poprawnie obsłużyć specjalne znaki w haśle
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
        except pika.exceptions.AMQPConnectionError:
            print("Czekam na RabbitMQ...")
            time.sleep(2)

    channel = connection.channel()
    channel.queue_declare(queue=JOB_QUEUE, durable=True)
    print('[*] Czekam na zlecenia. Naciśnij CTRL+C aby wyjść.')

    # Funkcja callback - co ma się stać, gdy przyjdzie wiadomość
    def callback(ch, method, properties, body):
        job_id_str = body.decode()
        
        try:
            # Próbuj konwertować na UUID (dla pewności)
            job_id = uuid.UUID(job_id_str)
            print(f"[+] Otrzymano zlecenie: {job_id}")
            process_job(job_id)
        except ValueError:
            print(f"[!] Otrzymano błędny job_id: {job_id_str}")
        except Exception as e:
            print(f"[!] Nieoczekiwany błąd podczas process_job: {e}")
        
        # Potwierdź RabbitMQ, że wiadomość została przetworzona
        ch.basic_ack(delivery_tag=method.delivery_tag)

    # Powiedz RabbitMQ, aby wysyłał do tego workera tylko jedną wiadomość na raz
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=JOB_QUEUE, on_message_callback=callback)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Zamykanie...")
        channel.stop_consuming()
        connection.close()

if __name__ == '__main__':
    # Upewnij się, że tabela 'jobs' istnieje, zanim worker wystartuje
    time.sleep(5) # Daj postgresowi chwilę
    Base.metadata.create_all(bind=engine)
    main()