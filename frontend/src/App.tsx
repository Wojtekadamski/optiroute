import { useState, useEffect } from 'react';
import axios from 'axios';
import  UploadComponent from './components/UploadComponent';
import  ResultsComponent  from './components/ResultsComponent';

// Definiujemy, jak wygląda odpowiedź z /results
interface JobResult {
  job_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  result: any; // Na razie 'any', docelowo tu będzie JSON z trasą
}

function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Ten hook uruchomi się, gdy tylko 'jobId' się zmieni
  // To jest nasz mechanizm "polligu"
  useEffect(() => {
    // Jeśli nie ma jobId, nic nie rób
    if (!jobId) return;

    // Resetuj poprzednie wyniki na wypadek nowego uploadu
    setJobResult(null);
    setError(null);

    const intervalId = setInterval(async () => {
      try {
        // Pytamy nasz results-service o status zadania
        // Nginx przekieruje to zapytanie do http://results-service:8000
        const response = await axios.get<JobResult>(`/api/v1/results/${jobId}`);
        
        const { status } = response.data;

        if (status === 'COMPLETED' || status === 'FAILED') {
          // Jeśli zadanie jest gotowe (lub się nie udało),
          // zatrzymaj pętlę i zapisz wynik
          clearInterval(intervalId);
          setJobResult(response.data);

          if (status === 'FAILED') {
            setError(response.data.result?.error || 'Nieznany błąd przetwarzania.');
          }
        }
        // Jeśli status to wciąż PENDING lub PROCESSING,
        // pętla wykona się ponownie za 2 sekundy
        
      } catch (err) {
        // Jeśli samo zapytanie o status się nie uda, zatrzymaj pętlę
        clearInterval(intervalId);
        setError('Nie można połączyć się z serwerem wyników.');
        console.error(err);
      }
    }, 2000); // Pytaj co 2 sekundy

    // Funkcja czyszcząca - zatrzyma pętlę, jeśli komponent się odmontuje
    return () => clearInterval(intervalId);

  }, [jobId]); // Uruchom ten efekt ponownie tylko, gdy 'jobId' się zmieni

  // Funkcja do resetowania aplikacji (by móc wysłać nowy plik)
  const handleReset = () => {
    setJobId(null);
    setJobResult(null);
    setError(null);
  };

  // ----- Logika Wyświetlania -----

  let content;
  if (error) {
    // 1. Stan BŁĘDU
    content = (
      <div className="text-red-500">
        <h2>Wystąpił błąd</h2>
        <p>{error}</p>
        <button onClick={handleReset} className="mt-4 p-2 bg-blue-500 text-white rounded">
          Spróbuj ponownie
        </button>
      </div>
    );
  } else if (jobResult) {
    // 2. Stan WYNIKÓW (COMPLETED)
    content = (
      <div>
        <ResultsComponent data={jobResult.result} />
        <button onClick={handleReset} className="mt-4 p-2 bg-blue-500 text-white rounded">
          Prześlij nowy plik
        </button>
      </div>
    );
  } else if (jobId) {
    // 3. Stan OCZEKIWANIA (PENDING/PROCESSING)
    content = (
      <div className="text-center">
        <h2 className="text-2xl font-semibold mb-2">Przetwarzanie pliku...</h2>
        <p className="text-gray-500">To może potrwać chwilę.</p>
        <p className="text-sm text-gray-400 mt-4">Job ID: {jobId}</p>
        {/* Prosty spinner */}
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mt-4"></div>
      </div>
    );
  } else {
    // 4. Stan POCZĄTKOWY (brak jobId)
    content = <UploadComponent onUploadSuccess={setJobId} onError={setError} />;
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-white rounded-lg shadow-xl p-8">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-6">
          OptiRoute - Optymalizator Tras
        </h1>
        {content}
      </div>
    </div>
  );
}

export default App;
