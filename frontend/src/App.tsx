import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Same shape as the Pydantic model `Station` in the API
type Station = {
  adresse: string;
  arrondissement: string | null;
  lat: number;
  lon: number;
  total: number;
  available: number;
  occupied: number;
  out_of_service: number;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const REFRESH_MS = 60_000; // 1 minute

function colorFor(s: Station) {
  if (s.available > 0) return "#16a34a";  // green: at least one free
  if (s.occupied > 0) return "#dc2626";   // red: all working points busy
  return "#9ca3af";                       // grey: nothing working
}

export default function App() {
  const [stations, setStations] = useState<Station[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  useEffect(() => {
    const load = () => {
      fetch(`${API_URL}/stations`)
        .then((res) => {
          if (!res.ok) throw new Error(`API error ${res.status}`);
          return res.json();
        })
        .then((data: Station[]) => {
          setStations(data);
          setError(null);
          setUpdatedAt(new Date());
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    };

    load();                                   // load once right away
    const id = setInterval(load, REFRESH_MS); // then every minute
    return () => clearInterval(id);           // cleanup when the component unmounts
  }, []);

  const available = stations.reduce((n, s) => n + s.available, 0);
  const total = stations.reduce((n, s) => n + s.total, 0);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "12px 16px" }}>
        <strong>Belib' Forecast</strong>{" — "}
        {loading
          ? "Loading…"
          : error
          ? `Error: ${error}`
          : `${available} / ${total} points available in ${stations.length} stations`}
        {updatedAt && (
          <small style={{ marginLeft: 12, color: "#6b7280" }}>
            updated {updatedAt.toLocaleTimeString("fr-FR")}
          </small>
        )}
      </header>

      <MapContainer center={[48.8566, 2.3522]} zoom={12} style={{ flex: 1 }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {stations.map((s) => (
          <CircleMarker
            key={s.adresse}
            center={[s.lat, s.lon]}
            radius={4 + 2 * Math.sqrt(s.total)}
            pathOptions={{ color: colorFor(s), fillOpacity: 0.8 }}
          >
            <Popup>
              <strong>{s.adresse}</strong>
              <br />
              {s.available} / {s.total} available
              <br />
              <small>
                {s.occupied} charging · {s.out_of_service} out of service
              </small>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}