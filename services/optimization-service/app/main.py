import os
import uuid
import pika
import time
import csv
import json
from sqlalchemy import create_engine, Column, String, DateTime, JSON, update
from sqlalchemy.dialects.postgresql import UUID
# Poprawiony import dla SQLAlchemy 2.0 (usuwa ostrzeżenie z logów)
from sqlalchemy.orm import sessionmaker, Session, declarative_base 
from sqlalchemy.sql import func

# --- [LOG STARTOWY] ---
# Ten print musi się pojawić jako pierwszy, gdy skrypt jest importowany
print("--- [OptiService] Skrypt main.py uruchomiony (poziom importu) ---", flush=True)

# NOWE IMPORTY: Importujemy nasze nowe funkcje
from geocoder import geocode_address
from optimizer import optimize_route_with_tomtom 

# --- 1. Konfiguracja Bazy Danych ---
# Używamy Twoich danych logowania jako domyślnych
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://optiroute:optiroute123@postgres/optiroute")

Base = declarative_base() # Użyj poprawnego declarative_base
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Model Job (Bez zmian)
class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, default="PENDING", index=True)
    # Ścieżka pliku musi pasować do Twojej konfiguracji docker-compose.yml
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

# --- 2. Konfiguracja RabbitMQ ---
# Używamy Twoich danych logowania jako domyślnych
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://optiroute:optiroute123@rabbitmq:5672/")
JOB_QUEUE = "job_queue"

# --- 3. Główna logika workera ---

def process_job(job_id):
    """
    Funkcja, która wykonuje całą logikę przetwarzania zlecenia.
    """
    db = get_db()
    job = None # Zdefiniuj job na zewnątrz bloku try
    try:
        print(f"[{job_id}] Rozpoczynam przetwarzanie...", flush=True)
        
        # 1. Pobierz zadanie z bazy
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            print(f"[{job_id}] BŁĄD: Nie znaleziono zlecenia w bazie.", flush=True)
            return

        # 2. Oznacz zadanie jako "PROCESSING"
        job.status = "PROCESSING"
        db.commit()

        # 3. Odczytaj plik CSV
        if not os.path.exists(job.input_file_path):
            raise FileNotFoundError(f"Plik {job.input_file_path} nie istnieje.")
        
        parsed_addresses = []
        with open(job.input_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row: 
                    # POPRAWKA: Łączymy wszystkie kolumny w jeden adres (np. "Sienkiewicza 20", "Wrocław")
                    full_address = ", ".join(row)
                    parsed_addresses.append(full_address) 
        
        print(f"[{job_id}] Znaleziono {len(parsed_addresses)} adresów w CSV.", flush=True)

        # --- Etap 1: Geokodowanie ---
        geocoded_stops = []
        for address in parsed_addresses:
            print(f"[{job_id}] Geokodowanie adresu: {address}", flush=True)
            coords = geocode_address(address)
            
            if coords:
                geocoded_stops.append({
                    "address": address,
                    "lat": coords[0],
                    "lon": coords[1]
                })
            else:
                geocoded_stops.append({
                    "address": address,
                    "error": "Nie znaleziono współrzędnych"
                })
            
            # WAŻNE: Polityka API Nominatim (max 1 zapytanie/sek)
            print(f"[{job_id}] Czekam 1 sekundę (polityka API Nominatim)...", flush=True)
            time.sleep(1)
        
        print(f"[{job_id}] Geokodowanie zakończone.", flush=True)

        # --- Etap 2: Optymalizacja Trasy ---
        
        # Filtruj tylko te przystanki, które mają współrzędne
        valid_stops = [stop for stop in geocoded_stops if "error" not in stop]
        
        if len(valid_stops) < 2:
            # Nie ma wystarczająco punktów do optymalizacji
            print(f"[{job_id}] Zbyt mało poprawnych punktów do optymalizacji. Zapisywanie wyników geokodowania.", flush=True)
            job.status = "COMPLETED"
            job.result = {
                "message": "Geokodowanie zakończone. Zbyt mało punktów (min. 2) do optymalizacji.",
                "processed_count": len(geocoded_stops),
                "geocoded_stops": geocoded_stops
            }
        else:
            # Mamy wystarczająco punktów, wywołaj TomTom
            print(f"[{job_id}] Rozpoczynam optymalizację trasy dla {len(valid_stops)} punktów...", flush=True)
            
            tomtom_result = optimize_route_with_tomtom(str(job_id), valid_stops)
            
            job.status = "COMPLETED"
            job.result = {
                "message": "Optymalizacja zakończona.",
                "geocoding_summary": geocoded_stops,
                "optimization_result": tomtom_result # Zapisujemy pełną odpowiedź z TomTom
            }
            print(f"[{job_id}] Zakończono pomyślnie. Zoptymalizowano {len(valid_stops)} punktów.", flush=True)

        db.commit()

    except Exception as e:
        # 5. Obsługa błędów
        print(f"[{job_id}] BŁĄD KRYTYCZNY: {e}", flush=True)
        if db.is_active:
            db.rollback()
        
        # Sprawdź, czy 'job' istnieje, zanim spróbujesz go zaktualizować
        job_to_fail = db.query(Job).filter(Job.id == job_id).first()
        if job_to_fail:
            job_to_fail.status = "FAILED"
            job_to_fail.result = {"error": str(e)}
            
            db.commit()
            # --- KONIEC POPRAWKI ---
    finally:
        db.close()

# --- 4. Funkcja Main (Bez zmian) ---

def main():
    print("--- [OptiService] Uruchamiam funkcję main() ---", flush=True)
    
    # Czekaj na RabbitMQ i połącz się
    connection = None
    print(f"--- [OptiService] Próbuję połączyć się z RabbitMQ pod adresem: {RABBITMQ_URL} ---", flush=True)
    
    while not connection:
        try:
            # Używamy pika.URLParameters, aby poprawnie obsłużyć specjalne znaki w haśle
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            print("--- [OptiService] POŁĄCZONO z RabbitMQ! ---", flush=True)
        except pika.exceptions.AMQPConnectionError:
            print("--- [OptiService] Nie można połączyć z RabbitMQ. Czekam 2s i próbuję ponownie...", flush=True)
            time.sleep(2)

    print("--- [OptiService] Tworzenie kanału RabbitMQ...", flush=True)
    channel = connection.channel()
    
    print(f"--- [OptiService] Deklarowanie kolejki: {JOB_QUEUE} ---", flush=True)
    channel.queue_declare(queue=JOB_QUEUE, durable=True)
    
    # Oryginalny log - teraz już wiemy, że się pojawi
    print('[*] Czekam na zlecenia. Naciśnij CTRL+C aby wyjść.', flush=True)

    # Funkcja callback - co ma się stać, gdy przyjdzie wiadomość
    def callback(ch, method, properties, body):
        job_id_str = body.decode()
        
        try:
            # Próbuj konwertować na UUID (dla pewności)
            job_id = uuid.UUID(job_id_str)
            print(f"[+] Otrzymano zlecenie: {job_id}", flush=True)
            process_job(job_id)
        except ValueError:
            print(f"[!] Otrzymano błędny job_id: {job_id_str}", flush=True)
        except Exception as e:
            print(f"[!] Nieoczekiwany błąd podczas process_job: {e}", flush=True)
        
        # Potwierdź RabbitMQ, że wiadomość została przetworzona
        print(f"--- [OptiService] Potwierdzam przetworzenie wiadomości (basic_ack) dla {job_id_str} ---", flush=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    # Powiedz RabbitMQ, aby wysyłał do tego workera tylko jedną wiadomość na raz
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=JOB_QUEUE, on_message_callback=callback)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Zamykanie...", flush=True)
        channel.stop_consuming()
        connection.close()

# --- 5. Główny punkt startowy (Bez zmian) ---

if __name__ == '__main__':
    print("--- [OptiService] Skrypt uruchomiony jako __main__ ---", flush=True)
    
    # Upewnij się, że tabela 'jobs' istnieje, zanim worker wystartuje
    print(f"--- [OptiService] Czekam 5s na start bazy danych ({DATABASE_URL})... ---", flush=True)
    time.sleep(5) # Daj postgresowi chwilę
    
    try:
        print("--- [OptiService] Inicjowanie bazy danych (Base.metadata.create_all)... ---", flush=True)
        Base.metadata.create_all(bind=engine)
        print("--- [OptiService] Inicjowanie bazy danych ZAKOŃCZONE ---", flush=True)
    except Exception as e:
        print(f"--- [OptiService] KRYTYCZNY BŁĄD podczas łączenia z bazą lub tworzenia tabel: {e} ---", flush=True)
        # Na razie pozwólmy mu iść dalej, może błąd jest w logice RabbitMQ
    
    main()