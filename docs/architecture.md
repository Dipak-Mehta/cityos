# CITYOS Phase 1 Architecture

## Components

- **Simulator:** generates normal and failure-scenario telemetry for three intersections.
- **API:** FastAPI service for ingestion, querying and risk classification.
- **PostgreSQL:** stores intersection metadata and telemetry history.
- **Prometheus:** scrapes API operational metrics.
- **Grafana:** visualizes telemetry-ingestion health.

## Data flow

```text
Simulator
   |
   | HTTP POST /api/v1/telemetry
   v
FastAPI -----> PostgreSQL
   |
   +----------> Prometheus -----> Grafana
   |
   +----------> Risk classification
```

## Design principles

- Simulate first; integrate real infrastructure only after validation and authorization.
- Keep safety-critical actions human-approved.
- Store telemetry without personal data in Phase 1.
- Keep services containerized and reproducible.
