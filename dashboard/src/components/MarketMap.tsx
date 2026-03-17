"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { MarketIndex } from "@/lib/api";

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

function trendColor(trend: string | null): string {
  if (trend === "up") return "#ea4335";
  if (trend === "down") return "#34a853";
  return "#fbbc04";
}

export default function MarketMap({ indices }: { indices: MarketIndex[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: [-98.5, 39.5],
      zoom: 3.8,
    });

    mapRef.current = map;

    map.on("load", () => {
      for (const idx of indices) {
        if (idx.lat == null || idx.lng == null) continue;

        const ratio = idx.load_to_truck_ratio ?? 1;
        const radius = Math.max(20, Math.min(50, ratio * 20));

        const el = document.createElement("div");
        el.style.width = `${radius}px`;
        el.style.height = `${radius}px`;
        el.style.borderRadius = "50%";
        el.style.backgroundColor = trendColor(idx.trend);
        el.style.opacity = "0.7";
        el.style.border = "2px solid white";
        el.style.cursor = "pointer";

        const popup = new mapboxgl.Popup({ offset: 15 }).setHTML(`
          <div style="font-family:Inter,sans-serif;font-size:13px;">
            <strong>${idx.region}</strong><br/>
            Load/Truck: <b>${ratio}</b><br/>
            Avg Rate: <b>$${idx.avg_rate_per_mile}/mi</b><br/>
            Trend: <b style="color:${trendColor(idx.trend)}">${idx.trend?.toUpperCase()}</b>
          </div>
        `);

        new mapboxgl.Marker({ element: el })
          .setLngLat([idx.lng, idx.lat])
          .setPopup(popup)
          .addTo(map);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [indices]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", borderRadius: 16, minHeight: 400 }}
    />
  );
}
