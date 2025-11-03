import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

// Definiujemy, jakie propsy przyjmuje nasz komponent
interface UploadProps {
  onUploadSuccess: (jobId: string) => void;
  onError: (message: string | null) => void;
}

function UploadComponent({ onUploadSuccess, onError }: UploadProps) {
  const [isLoading, setIsLoading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) {
      onError('Nie wybrano pliku lub plik jest nieprawidłowy.');
      return;
    }

    const file = acceptedFiles[0];

    // Sprawdź, czy to na pewno CSV po stronie klienta
    if (!file.name.endsWith('.csv')) {
      onError('Nieprawidłowy typ pliku. Proszę wybrać plik .csv');
      return;
    }

    setIsLoading(true);
    onError(null); // Resetuj błędy

    // Stwórz FormData, aby wysłać plik
    const formData = new FormData();
    formData.append('file', file); // 'file' musi zgadzać się z nazwą w FastAPI

    try {
      // Wyślij plik do naszego upload-service
      // Nginx przekieruje to zapytanie
      const response = await axios.post('/api/v1/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Jeśli się uda, przekaż job_id do rodzica (App.tsx)
      onUploadSuccess(response.data.job_id);

    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        // Jeśli backend zwrócił błąd (np. 400), przekaż go
        onError(err.response.data.detail || 'Błąd serwera.');
      } else {
        onError('Nie można połączyć się z serwerem.');
      }
      console.error(err);
      setIsLoading(false);
    }
  }, [onUploadSuccess, onError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'], // Akceptuj tylko pliki CSV
    },
    maxFiles: 1,
  });

  // --- ZAKTUALIZOWANY RETURN (UŻYWA KLAS Z App.css) ---
  return (
    <div
      {...getRootProps()}
      // Używamy klas z App.css i dodajemy styl 'loading'
      className={`upload-box ${isDragActive ? 'upload-box-active' : ''} ${isLoading ? 'loading-opacity' : ''}`}
      style={isLoading ? { opacity: 0.5 } : {}} // Dodajemy styl inline dla ładowania
    >
      <input {...getInputProps()} />
      {isLoading ? (
        <p>Przesyłanie...</p>
      ) : isDragActive ? (
        <p>Upuść plik tutaj...</p>
      ) : (
        <p>
          Przeciągnij i upuść plik .csv, albo kliknij by go wybrać.
        </p>
      )}
    </div>
  );
}

export default UploadComponent;