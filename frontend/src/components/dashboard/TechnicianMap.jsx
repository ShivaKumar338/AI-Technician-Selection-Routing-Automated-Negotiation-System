import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import { Skeleton } from "../ui/Skeleton";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const HYDERABAD_CENTER = [17.385, 78.4867];

export default function TechnicianMap({ technicians, loading }) {
  const available = (technicians || []).filter((tech) => tech.available);

  return (
    <div className="card-surface overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Live Technician Map</h2>
          <p className="text-sm text-muted">{available.length} technicians available</p>
        </div>
      </div>
      <div className="h-[360px] w-full">
        {loading ? (
          <Skeleton className="h-full w-full rounded-none" />
        ) : (
          <MapContainer
            center={HYDERABAD_CENTER}
            zoom={11}
            scrollWheelZoom
            className="h-full w-full"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            {available.map((tech) => (
              <Marker
                key={tech.id}
                position={[tech.lat, tech.lng]}
                icon={defaultIcon}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-semibold">{tech.name}</p>
                    <p>Rating: {tech.rating}/5</p>
                    <p>From {tech.rate_min} INR</p>
                    <p>{(tech.skills || []).join(", ")}</p>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}
      </div>
    </div>
  );
}
