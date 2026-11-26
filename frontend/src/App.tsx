import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Same shape as the Pydantic model `Point` in your API
type Point = {
  id_pdc: string;
  statut: string;
  last_updated: string;
  adresse_station: string | null;
  arrondissement: string | null;
  lat: number | null;
  lon: number | null;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

const COLORS: Record<string, string> = {
  "Disponible": "#16a34a",          // green
  "Occupé (en charge)": "#dc2626",  // red
};
const colorFor = (statut: string) => COLORS[statut] ?? "#9ca3af"; // grey for the rest

export default function App() {
  const [points, setPoints] = useState<Point[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/points`)
      .then((res) => {
        if (!res.ok) throw new Error(`API error ${res.status}`);
        return res.json();
      })
      .then(setPoints)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const located = points.filter((p) => p.lat !== null && p.lon !== null);
  const available = points.filter((p) => p.statut === "Disponible").length;

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "12px 16px" }}>
        <strong>Belib' Forecast</strong>{" — "}
        {loading
          ? "Loading…"
          : error
          ? `Error: ${error}`
          : `${available} / ${points.length} charging points available`}
      </header>

      <MapContainer center={[48.8566, 2.3522]} zoom={12} style={{ flex: 1 }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {located.map((p) => (
          <CircleMarker
            key={p.id_pdc}
            center={[p.lat!, p.lon!]}
            radius={5}
            pathOptions={{ color: colorFor(p.statut), fillOpacity: 0.8 }}
          >
            <Popup>
              <strong>{p.adresse_station}</strong>
              <br />
              {p.statut}
              <br />
              <small>Updated {new Date(p.last_updated).toLocaleString("fr-FR")}</small>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}