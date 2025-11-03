import { useState, useEffect } from 'react';
import axios from 'axios';
import UploadComponent from './components/UploadComponent';
import ResultsComponent from './components/ResultsComponent';
import './App.css'; // Upewnij się, że ten import istnieje

interface JobResult {
  job_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  result: any;
}

function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ... (CAŁA LOGIKA useEffect POZOSTAJE BEZ ZMIAN) ...
  useEffect(() => {
    if (!jobId) return;
    setJobResult(null);
    setError(null);
    const intervalId = setInterval(async () => {
      try {
        const response = await axios.get<JobResult>(`/api/v1/results/${jobId}`);
        const { status } = response.data;
        if (status === 'COMPLETED' || status === 'FAILED') {
          clearInterval(intervalId);
          setJobResult(response.data);
          if (status === 'FAILED') {
            setError(response.data.result?.error || 'Nieznany błąd przetwarzania.');
          }
        }
      } catch (err) {
        clearInterval(intervalId);
        setError('Nie można połączyć się z serwerem wyników.');
        console.error(err);
      }
    }, 2000);
    return () => clearInterval(intervalId);
  }, [jobId]);

  const handleReset = () => {
    setJobId(null);
    setJobResult(null);
    setError(null);
  };

  // ----- Logika Wyświetlania (z nowymi klasami CSS) -----

  let content;
  if (error) {
    content = (
      <div>
        {/* ResultsComponent sam obsłuży wyświetlanie błędu */}
        <ResultsComponent data={{ error: error }} />
        <button onClick={handleReset} className="button-primary">
          Spróbuj ponownie
        </button>
      </div>
    );
  } else if (jobResult) {
    content = (
      <div>
        <ResultsComponent data={jobResult.result} />
        <button onClick={handleReset} className="button-primary">
          Prześlij nowy plik
        </button>
      </div>
    );
  } else if (jobId) {
    content = (
      <div className="results-box" style={{ textAlign: 'center' }}>
        <h2 className="results-section-header">Przetwarzanie pliku...</h2>
        <p style={{ color: '#9CA3AF' }}>To może potrwać chwilę.</p>
        <p style={{ fontSize: '0.875rem', color: '#6B7280', marginTop: '1rem' }}>Job ID: {jobId}</p>
        <div className="loading-spinner"></div>
      </div>
    );
  } else {
    content = <UploadComponent onUploadSuccess={setJobId} onError={setError} />;
  }

  return (
    // Używamy klas z App.css
    <div className="app-container">
      <h1 className="app-header">
        OptiRoute - Optymalizator Tras
      </h1>
      {content}
    </div>
  );
}

export default App;