## OptiRoute

Kompleksowy projekt demonstracyjny implementujący architekturę mikroserwisów do obsługi przesyłania, optymalizacji tras i agregacji wyników.

Projekt zawiera frontend (React + Vite) oraz kilka usług backendowych w Pythonie, uruchamianych za pomocą Docker Compose.

### Status projektu (na dzień 3 listopada 2025)

#### Zaimplementowane funkcjonalności:
- ✅ Podstawowa struktura mikroserwisów
- ✅ Upload plików CSV z adresami (drag & drop)
- ✅ Geokodowanie adresów (Nominatim API)
- ✅ Kolejkowanie zadań (RabbitMQ)
- ✅ System śledzenia statusu zadań w czasie rzeczywistym
- ✅ Integracja z TomTom Routing API (optymalizacja + geometria trasy)
- ✅ Agregacja danych środowiskowych (pogoda, jakość powietrza)
- ✅ Interaktywna wizualizacja tras z react-leaflet
- ✅ Obliczanie i wizualizacja zoptymalizowanej kolejności przystanków
- ✅ Podgląd szczegółowych informacji o trasie (czas, dystans)
- ✅ Obsługa błędów geokodowania i API
- ✅ Persystencja danych w PostgreSQL
- ✅ Load balancing i reverse proxy (Nginx)

#### Modyfikatory tras:
System uwzględnia następujące czynniki wpływające na czas przejazdu:
- Opady deszczu: +20% do czasu przejazdu
- Opady śniegu: +30% do czasu przejazdu
- Silny wiatr (>10 m/s): +10% do czasu przejazdu
- Zła jakość powietrza (PM2.5 > 50): +10% do czasu przejazdu
- Bardzo zła jakość powietrza (PM10 > 100): +15% do czasu przejazdu

#### W trakcie rozwoju:
- 🚧 Optymalizacja wydajności geokodowania
- 🚧 Rozszerzenie modyfikatorów tras
- 🚧 Testy jednostkowe i integracyjne
- 🚧 Dokumentacja API (Swagger/OpenAPI)

## Zawartość repozytorium

### Struktura projektu
- `frontend/` — aplikacja kliencka napisana w TypeScript z Vite
  - Interfejs użytkownika z obsługą drag-and-drop plików CSV
  - Interaktywna mapa z użyciem react-leaflet
  - Śledzenie statusu zadań w czasie rzeczywistym
  - Wizualizacja zoptymalizowanych tras

### Serwisy backendowe
- `services/upload-service/` 
  - Przyjmowanie i walidacja plików CSV
  - Integracja z PostgreSQL do śledzenia zadań
  - Kolejkowanie w RabbitMQ
  - Obsługa współdzielonych wolumenów

- `services/optimization-service/`
  - Geokodowanie adresów (Nominatim API)
  - Optymalizacja tras (TomTom Routing API)
  - Worker do przetwarzania zadań z kolejki
  - Aktualizacja statusów i wyników

- `services/data-aggregator-service/`
  - Integracja z OpenWeatherMap API
  - Integracja z OpenAQ API
  - Obliczanie modyfikatorów czasu przejazdu
  - Agregacja danych środowiskowych

- `services/results-service/`
  - REST API do pobierania wyników
  - Integracja z bazą danych PostgreSQL
  - Monitorowanie statusu zadań
  - Format JSON dla wyników optymalizacji

### Infrastruktura
- `nginx/` — reverse proxy i serwer statyczny
  - Load balancing
  - Routing żądań do mikroserwisów
  - Serwowanie aplikacji frontendowej
  - Konfiguracja CORS i limitów

- `docker-compose.yml` — orkiestracja kontenerów
  - Definicje wszystkich serwisów
  - Konfiguracja sieci i wolumenów
  - Zarządzanie sekretami i zmiennymi środowiskowymi
  - Zależności między serwisami

> Uwaga: Szczegółowa implementacja serwisów znajduje się w katalogach `services/*/app/` — tam znajdziesz pliki `main.py`, `optimizer.py`, `geocoder.py` i inne.

## Wymagania

- Docker (>= 20.x)
- Docker Compose
- Node.js (jeśli chcesz uruchamiać frontend lokalnie)
- Python 3.9+ (jeśli chcesz uruchamiać usługi lokalnie bez kontenerów)

## Szybki start (Docker Compose)

Najprostszy sposób uruchomienia całego stosu to użycie Docker Compose. W katalogu głównym projektu uruchom:

```powershell
docker-compose up --build -d
```

Aby obserwować logi:

```powershell
docker-compose logs -f
```

Zatrzymanie i usunięcie kontenerów:

```powershell
docker-compose down
```

Po uruchomieniu:

- Frontend najprawdopodobniej będzie dostępny pod adresem http://localhost:80 (konfiguracja w `nginx/nginx.conf` i `docker-compose.yml`).
- Usługi backendowe będą wystawione wewnątrz sieci Docker — sprawdź `docker-compose.yml` dla mapowania portów.

## Uruchamianie frontend lokalnie (dev)

Jeśli chcesz pracować nad frontendem lokalnie bez kontenerów:

```powershell
cd frontend
npm install
npm run dev
```

Frontend wykorzystuje Vite; domyślnie uruchomi się na porcie skonfigurowanym w `vite.config.ts`.

Jeśli frontend nie jest jeszcze zainicjalizowany (np. gdy tworzysz projekt od zera), możesz utworzyć projekt Vite i zainstalować zależności mapy/drag-and-drop:

```powershell
# tylko przy pierwszej inicjalizacji projektu frontend
npm create vite@latest . -- --template react-ts
npm install react-leaflet leaflet
npm install -D @types/react-leaflet @types/leaflet
npm install react-dropzone axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install -D @tailwindcss/postcss
```

## Uruchamianie usług backendowych lokalnie (bez Dockera)

Każdy serwis ma swój katalog z `requirements.txt`. Przykładowy sposób uruchomienia pojedynczego serwisu:

```powershell
cd services/optimization-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app/main.py
```

Uwaga: w środowisku lokalnym może być konieczne ustawienie zmiennych środowiskowych (np. porty, dane konfiguracyjne). Sprawdź pliki `main.py` w katalogach `services/*/app/` aby dowiedzieć się, jakie zmienne są wymagane.

## Konfiguracja i punkty końcowe (API)

### Upload Service
- `POST /api/v1/upload`
  - Przyjmuje: `multipart/form-data` z plikiem CSV
  - Zwraca: `{ "job_id": "uuid" }`
  - Waliduje format pliku i tworzy nowe zadanie

### Results Service
- `GET /api/v1/results/{job_id}`
  - Zwraca status i wyniki zadania
  - Statusy: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`
  - Format wyników zawiera zgeokodowane punkty i zoptymalizowaną trasę

### Data Aggregator Service
- `GET /api/v1/environment`
  - Parametry: `city` (nazwa miasta)
  - Zwraca dane środowiskowe i modyfikatory:
    - Warunki pogodowe
    - Jakość powietrza
    - Całkowity modyfikator czasu przejazdu

### Format danych wejściowych (CSV)
```csv
adres
"ul. Krakowska 1, Wrocław"
"ul. Świdnicka 5, Wrocław"
"pl. Grunwaldzki 10, Wrocław"
```

### Format wyników (JSON)
```json
{
  "status": "COMPLETED",
  "result": {
    "geocoded_stops": [
      {
        "address": "ul. Krakowska 1, Wrocław",
        "lat": 51.1079,
        "lon": 17.0385
      }
    ],
    "route": {
      "total_distance": 12500,
      "total_time": 1800,
      "points": [...]
    },
    "environment": {
      "weather_modifier": 1.2,
      "air_quality_modifier": 1.1,
      "total_modifier": 1.32
    }
  }
}
```

## Struktura katalogów (skrót)

```
./
├─ docker-compose.yml
├─ frontend/
├─ nginx/
└─ services/
   ├─ upload-service/
   ├─ data-aggregator-service/
   ├─ optimization-service/
   └─ results-service/
```

## Testy

Obecnie projekt nie zawiera zautomatyzowanej baterii testów. Dobrym pierwszym krokiem będzie dodanie prostych testów jednostkowych do każdego serwisu (pytest) oraz testów integracyjnych dla przepływu Docker Compose.

## Wkład i rozwój

Jeśli chcesz wnieść wkład:

1. Utwórz issue z opisem proponowanej zmiany.
2. Zrób fork i pracuj na gałęzi feature/<krótki-opis>.
3. Wyślij pull request z opisem zmian i instrukcjami jak przetestować.

Pamiętaj o dodaniu testów dla nowych funkcji i utrzymaniu spójności stylu kodu.

## Licencja

Brak jawnie określonej licencji w repozytorium. Jeśli chcesz udostępnić projekt publicznie, rozważ dodanie pliku `LICENSE` (np. MIT) i umieszczenie wpisu o licencji w tym README.

## Pomoc i kontakt

Jeśli masz pytania dotyczące projektu, umieść issue w repozytorium lub skontaktuj się z właścicielem repozytorium.

---

Plik README zawiera podstawowe instrukcje szybkiego startu i wskazówki deweloperskie. Jeśli chcesz, mogę dopisać szczegółową dokumentację endpointów (OpenAPI), przykładowe payloady lub instrukcje CI/CD.

## Postęp prac i następne kroki

Aktualny status znajduje się także w pliku `TODO.md` w katalogu głównym repozytorium — tam będziemy dodawać kolejne etapy rozwoju, priorytety i krótkie opisy zadań.


