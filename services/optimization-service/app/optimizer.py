import httpx
import os
from typing import List, Dict, Any, Optional

# Adres URL API TomTom Waypoint Optimization
TOMTOM_API_URL = "https://api.tomtom.com/routing/waypointoptimization/1"

# Funkcja pomocnicza do formatowania lokalizacji dla TomTom
def format_locations_for_tomtom(stops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Konwertuje naszą listę przystanków na format JSON wymagany przez TomTom.
    (Bez zmian)
    """
    locations = []
    for stop in stops:
        if "lat" in stop and "lon" in stop:
            locations.append({
                "point": {
                    "latitude": stop["lat"],
                    "longitude": stop["lon"]
                }
            })
    return locations


# Główna funkcja optymalizacji trasy z TomTom
def optimize_route_with_tomtom(job_id: str, stops: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Wysyła listę przystanków do TomTom Waypoint Optimization API
    i zwraca zoptymalizowaną trasę.
    """
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key or api_key == "TWOJ_KLUCZ_API_WKLEJ_TUTAJ":
        print(f"[{job_id}] BŁĄD: Brak klucza TOMTOM_API_KEY w zmiennych środowiskowych.", flush=True)
        raise ValueError("Brak klucza TOMTOM_API_KEY. Sprawdź docker-compose.yml")

    locations_payload = format_locations_for_tomtom(stops)
    
    if len(locations_payload) < 2:
        print(f"[{job_id}] Błąd: Zbyt mało poprawnych punktów do optymalizacji ({len(locations_payload)}).", flush=True)
        return {"error": "Zbyt mało poprawnych punktów do optymalizacji (wymagane min. 2)."}

    # Budujemy pełny URL z kluczem API
    url = f"{TOMTOM_API_URL}?key={api_key}"
    
    # budowanie ładunku żądania (JSON) 
    payload = {
        "waypoints": locations_payload,
        "options": {
            "travelMode": "car",
            "traffic": "live",
            "departAt": "now" 
        }
    }
    # Logowanie wysyłanych danych
    print(f"[{job_id}] Wysyłanie {len(locations_payload)} punktów do TomTom API (Waypoint Optimization) na adres: {TOMTOM_API_URL}", flush=True)
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            print(f"[{job_id}] Otrzymano pomyślną odpowiedź z TomTom.", flush=True)
            return data

    except httpx.HTTPStatusError as e:
        print(f"[{job_id}] Błąd HTTP podczas optymalizacji TomTom: {e.response.status_code}", flush=True)
        print(f"[{job_id}] Odpowiedź błędu: {e.response.text}", flush=True)
        raise ValueError(f"Błąd TomTom API: {e.response.text}")
    except Exception as e:
        print(f"[{job_id}] Nieoczekiwany błąd podczas optymalizacji TomTom: {e}", flush=True)
        raise ValueError(f"Nieoczekiwany błąd podczas optymalizacji: {e}")