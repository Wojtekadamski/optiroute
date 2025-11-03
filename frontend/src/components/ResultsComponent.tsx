// Ważne: Przeniesiemy ten import do main.tsx, aby uniknąć problemów
// import 'leaflet/dist/leaflet.css'; 
import MapComponent from './MapComponent';

// --- Definicje typów (bez zmian) ---
interface ResultsProps {
  data: any;
}
interface GeocodedStop {
  address: string;
  lat?: number;
  lon?: number;
  error?: string;
}
interface RouteSummary {
  lengthInMeters: number;
  travelTimeInSeconds: number;
}
interface GeometryPoint {
  latitude: number;
  longitude: number;
}
interface OptimizationResult {
  optimizedOrder: number[];
  summary: RouteSummary;
  geometry: GeometryPoint[] | null; 
}

// --- Funkcje pomocnicze (bez zmian) ---
function formatTime(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  let parts = [];
  if (hours > 0) parts.push(`${hours} godz.`);
  if (minutes > 0 || parts.length === 0) parts.push(`${minutes} minut`);
  return parts.join(' ');
}
function formatDistance(totalMeters: number): string {
  const kilometers = totalMeters / 1000;
  return `${kilometers.toFixed(2)} km`;
}

// --- Główny komponent (Zmieniony RETURN) ---
function ResultsComponent({ data }: ResultsProps) {
  
  // Scenariusz błędu (używa klas z App.css)
  if (data.error) {
    return (
      // Używamy .results-box do spójnego wyglądu
      <div className="results-box" style={{ backgroundColor: '#450a0a', borderColor: '#dc2626', borderWidth: '1px' }}>
        <h2 className="results-section-header" style={{ color: '#f87171', textAlign: 'center' }}>
          Wystąpił błąd
        </h2>
        <pre className="results-json-pre" style={{ color: '#fca5a5' }}>
          {data.error}
        </pre>
      </div>
    );
  }

  // --- SCENARIUSZ 2: Sukces (Logika bez zmian) ---
  const { geocoding_summary, optimization_result } = data;
  const resultData: OptimizationResult = optimization_result;

  if (!geocoding_summary || !resultData || !resultData.summary || !resultData.optimizedOrder) {
    return <p>Otrzymano niekompletne dane z serwera.</p>;
  }

  const originalAddresses: GeocodedStop[] = geocoding_summary;
  const optimizedOrder: number[] = resultData.optimizedOrder;
  const summary: RouteSummary = resultData.summary; 
  const sortedAddresses: GeocodedStop[] = optimizedOrder.map(index => originalAddresses[index]);
  const mapStops = sortedAddresses.filter(
    (stop): stop is { address: string; lat: number; lon: number } => 
      stop.lat !== undefined && stop.lon !== undefined
  );
  const routeGeometry = resultData.geometry;

  // --- ZAKTUALIZOWANY RETURN (UŻYWA KLAS Z App.css) ---
  return (
    <div>
      <h2 
        className="results-section-header" 
        style={{ textAlign: 'center', color: '#34D399', fontSize: '1.5rem', marginBottom: '1.5rem' }}
      >
        {data.message || 'Optymalizacja zakończona.'}
      </h2>
      
      <div className="results-box">
        <h3 className="results-section-header" style={{ textAlign: 'center' }}>
          Podsumowanie Trasy
        </h3>
        <div className="results-summary-box">
          <div>
            <span className="results-summary-label">Całkowity Czas</span>
            <span className="results-summary-value">
              {formatTime(summary.travelTimeInSeconds)}
            </span>
          </div>
          <div>
            <span className="results-summary-label">Całkowity Dystans</span>
            <span className="results-summary-value">
              {formatDistance(summary.lengthInMeters)}
            </span>
          </div>
        </div>
      </div>
      
      <div className="map-container">
        <MapComponent stops={mapStops} geometry={routeGeometry} />
      </div>
      
      <h3 className="results-section-header">
        Zoptymalizowana kolejność przystanków:
      </h3>
      <ol className="results-box results-list">
        {sortedAddresses.map((stop, index) => (
          <li key={index}>
            {stop.address}
            {stop.error && (
              <span style={{ fontSize: '0.875rem', color: '#EF4444', marginLeft: '0.5rem' }}>
                ({stop.error})
              </span>
            )}
          </li>
        ))}
      </ol>

      <details className="results-json-details">
        <summary>
          Pokaż pełną odpowiedź JSON z backendu
        </summary>
        <pre className="results-json-pre">
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export default ResultsComponent;