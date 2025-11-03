## OptiRoute

Kompleksowy projekt demonstracyjny implementujący architekturę mikroserwisów do obsługi przesyłania, optymalizacji tras i agregacji wyników.

Projekt zawiera frontend (React + Vite) oraz kilka usług backendowych w Pythonie, uruchamianych za pomocą Docker Compose.

## Zawartość repozytorium

- `frontend/` — aplikacja kliencka napisana w TypeScript z Vite (interfejs użytkownika, mapy, upload plików)
- `services/upload-service/` — serwis odpowiadający za przyjmowanie plików i ich wstępne przetwarzanie
- `services/optimization-service/` — główny serwis optymalizujący trasy (geokoder + optimizer)
- `services/data-aggregator-service/` — agreguje dane wejściowe do formatu potrzebnego optymalizatorowi
- `services/results-service/` — serwis odpowiedzialny za przechowywanie/udostępnianie wyników
- `nginx/` — konfiguracja Nginx do reverse-proxy/serwowania frontend
- `docker-compose.yml` — kompozycja wszystkich usług do szybkiego uruchomienia

> Uwaga: implementacja serwisów znajduje się w katalogach `services/*/app/` — tam znajdziesz pliki `main.py`, `optimizer.py`, `geocoder.py` i inne.

## Wymagania

- Docker (>= 20.x)
- Docker Compose
- Node.js (jeśli chcesz uruchamiać frontend lokalnie)
- Python 3.9+ (jeśli chcesz uruchamiać usługi lokalnie bez kontenerów)

## Szybki start (Docker Compose)

załadowanie pakietów do frontendu (z nodejs)
```powershell
npm create vite@latest . -- --template react-ts
npm install react-leaflet leaflet
npm install -D @types/react-leaflet @types/leaflet
npm install react-dropzone axios
```

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

## Konfiguracja i punkty końcowe

Każdy serwis wystawia swoje endpointy w `services/<nazwa>/app/main.py` — tam znajdują się szczegóły dostępnych tras HTTP i wymaganych payloadów. Przykładowe role serwisów:

- upload-service: przyjmowanie plików/CSV i wysyłanie ich do agregatora
- data-aggregator-service: transformacja i walidacja danych wejściowych
- optimization-service: geokodowanie i optymalizacja tras
- results-service: przechowywanie oraz udostępnianie wyników optymalizacji

Jeśli chcesz dodać szczegółową dokumentację endpointów, rozważ wygenerowanie OpenAPI/Swagger lub dopisanie krótkiego opisu endpoints w tym pliku README.

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
