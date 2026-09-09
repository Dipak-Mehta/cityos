import os
from datetime import datetime, timezone
from typing import Any

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://cityos:cityos_dev_password@postgres:5432/cityos")
DB_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai:8010").rstrip("/")

app = FastAPI(title="CITYOS API", version="0.2.0")
telemetry_counter = Counter("cityos_telemetry_total", "Telemetry records received")
ai_analysis_counter = Counter("cityos_ai_analysis_total", "AI analyses requested")
ai_analysis_error_counter = Counter("cityos_ai_analysis_errors_total", "AI analyses that failed")


def query(sql: str, params: tuple[Any, ...] = ()):
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def execute(sql: str, params: tuple[Any, ...] = ()):
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if cur.description else []
        conn.commit()
        return rows


def ensure_ai_table():
    execute(
        """
        CREATE TABLE IF NOT EXISTS ai_analysis (
            id BIGSERIAL PRIMARY KEY,
            telemetry_id BIGINT REFERENCES telemetry(id) ON DELETE SET NULL,
            intersection_id VARCHAR(64) NOT NULL REFERENCES intersections(id),
            risk VARCHAR(16) NOT NULL,
            provider VARCHAR(32),
            model VARCHAR(128),
            analysis TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    execute("CREATE INDEX IF NOT EXISTS idx_ai_analysis_intersection_time ON ai_analysis(intersection_id, created_at DESC)")
    execute("CREATE INDEX IF NOT EXISTS idx_ai_analysis_risk_time ON ai_analysis(risk, created_at DESC)")


@app.on_event("startup")
def startup():
    ensure_ai_table()


@app.get("/health")
def health():
    try:
        query("SELECT 1")
        return {"status": "ok", "service": "cityos-api"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def calculate_risk(payload: dict[str, Any]) -> str:
    if payload["signal_latency"] > 3 or payload["error_count"] >= 10 or payload["power_voltage"] < 210:
        return "HIGH"
    if payload["signal_latency"] > 2 or payload["error_count"] >= 5 or payload["power_voltage"] < 220:
        return "MEDIUM"
    return "LOW"


async def request_ai_analysis(
    intersection_id: str,
    telemetry_id: int,
    telemetry: dict[str, Any],
    risk: str,
):
    ai_analysis_counter.inc()
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/analyze",
                json={
                    "intersection_id": intersection_id,
                    "telemetry": telemetry,
                    "risk": risk,
                },
            )
            response.raise_for_status()
            result = response.json()

        execute(
            """
            INSERT INTO ai_analysis
                (telemetry_id, intersection_id, risk, provider, model, analysis)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                telemetry_id,
                intersection_id,
                risk,
                result.get("provider"),
                result.get("model"),
                result.get("analysis", ""),
            ),
        )
    except Exception:
        ai_analysis_error_counter.inc()


@app.post("/api/v1/telemetry")
async def ingest(payload: dict[str, Any]):
    required = {"intersection_id", "traffic_volume", "signal_latency", "power_voltage", "error_count"}
    missing = required - payload.keys()
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {sorted(missing)}")

    ts = payload.get("timestamp") or datetime.now(timezone.utc)
    rows = execute(
        """
        INSERT INTO telemetry
            (intersection_id, timestamp, traffic_volume, signal_latency, power_voltage, error_count)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (
            payload["intersection_id"],
            ts,
            payload["traffic_volume"],
            payload["signal_latency"],
            payload["power_voltage"],
            payload["error_count"],
        ),
    )
    telemetry_id = rows[0][0]
    telemetry_counter.inc()

    risk = calculate_risk(payload)
    if risk in {"HIGH", "MEDIUM"}:
        await request_ai_analysis(
            payload["intersection_id"],
            telemetry_id,
            {
                "traffic_volume": payload["traffic_volume"],
                "signal_latency": payload["signal_latency"],
                "power_voltage": payload["power_voltage"],
                "error_count": payload["error_count"],
            },
            risk,
        )

    return {"accepted": True, "intersection_id": payload["intersection_id"], "risk": risk, "telemetry_id": telemetry_id}


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


@app.get("/api/v1/ai/analyses")
def ai_analyses(limit: int = 20):
    rows = query(
        """
        SELECT id, intersection_id, telemetry_id, risk, provider, model, analysis, created_at
        FROM ai_analysis
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (min(limit, 100),),
    )
    keys = ["id", "intersection_id", "telemetry_id", "risk", "provider", "model", "analysis", "created_at"]
    return [dict(zip(keys, row)) for row in rows]


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
