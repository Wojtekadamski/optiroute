interface ResultsProps {
  data: any; // Otrzymany JSON z bazy
}

function ResultsComponent({ data }: ResultsProps) {
  return (
    <div>
      <h2 className="text-2xl font-semibold text-green-600 mb-4">
        Zlecenie Ukończone!
      </h2>
      <p className="mb-2">Otrzymane dane z backendu (na razie to tylko symulacja):</p>
      <pre className="bg-gray-900 text-white p-4 rounded-md overflow-x-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
      
      {/* MIEJSCE NA MAPĘ W PRZYSZŁOŚCI:
        Gdy backend będzie zwracał współrzędne,
        odkomentujemy i użyjemy MapComponent.

        <div className="mt-6" style={{ height: '400px', width: '100%' }}>
          <MapComponent routeData={data.optimized_route} />
        </div>
      */}
    </div>
  );
}

export default ResultsComponent;
