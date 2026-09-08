import os
from datetime import datetime, timezone
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, generate_latest
from fastapi.responses import Response

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://cityos:cityos_dev_password@postgres:5432/cityos")
DB_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)

app = FastAPI(title="CITYOS API", version="0.1.0")
telemetry_counter = Counter("cityos_telemetry_total", "Telemetry records received")


def query(sql: str, params: tuple[Any, ...] = ()):
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


@app.get("/health")
def health():
    try:
        query("SELECT 1")
        return {"status": "ok", "service": "cityos-api"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/v1/telemetry")
def ingest(payload: dict[str, Any]):
    required = {"intersection_id", "traffic_volume", "signal_latency", "power_voltage", "error_count"}
    missing = required - payload.keys()
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {sorted(missing)}")

    ts = payload.get("timestamp") or datetime.now(timezone.utc)
    query(
        "INSERT INTO telemetry (intersection_id, timestamp, traffic_volume, signal_latency, power_voltage, error_count) VALUES (%s,%s,%s,%s,%s,%s)",
        (payload["intersection_id"], ts, payload["traffic_volume"], payload["signal_latency"], payload["power_voltage"], payload["error_count"]),
    )
    telemetry_counter.inc()
    return {"accepted": True, "intersection_id": payload["intersection_id"]}


@app.get("/api/v1/telemetry/latest")
def latest(limit: int = 20):
    rows = query("SELECT intersection_id, timestamp, traffic_volume, signal_latency, power_voltage, error_count FROM telemetry ORDER BY timestamp DESC LIMIT %s", (min(limit, 100),))
    return [dict(zip(["intersection_id", "timestamp", "traffic_volume", "signal_latency", "power_voltage", "error_count"], row)) for row in rows]


@app.get("/api/v1/intersections")
def intersections():
    rows = query("SELECT id, name, latitude, longitude FROM intersections ORDER BY id")
    return [dict(zip(["id", "name", "latitude", "longitude"], row)) for row in rows]


@app.get("/api/v1/anomalies")
def anomalies():
    rows = query("""
        SELECT t.intersection_id, t.timestamp, t.traffic_volume, t.signal_latency,
               t.power_voltage, t.error_count,
               CASE WHEN t.signal_latency > 3 OR t.error_count >= 10 OR t.power_voltage < 210 THEN 'HIGH'
                    WHEN t.signal_latency > 2 OR t.error_count >= 5 OR t.power_voltage < 220 THEN 'MEDIUM'
                    ELSE 'LOW' END AS risk
        FROM telemetry t
        WHERE t.timestamp = (SELECT MAX(t2.timestamp) FROM telemetry t2 WHERE t2.intersection_id=t.intersection_id)
        ORDER BY t.timestamp DESC
    """)
    keys = ["intersection_id", "timestamp", "traffic_volume", "signal_latency", "power_voltage", "error_count", "risk"]
    return [dict(zip(keys, row)) for row in rows]


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
