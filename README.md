# CITYOS

**The City That Fixes Itself**

CITYOS is an AI-powered infrastructure operations platform inspired by DevOps observability. Phase 1 builds a safe, simulated environment for monitoring traffic intersections and detecting infrastructure anomalies before they become incidents.

## Phase 1 MVP

- Simulated traffic intersections
- Continuous telemetry generation
- FastAPI backend
- PostgreSQL storage
- Rule-based anomaly detection
- Docker Compose local environment
- Health and telemetry APIs
- Prometheus metrics
- Grafana dashboard provisioning

### Architecture

```text
Traffic Simulator -> FastAPI -> PostgreSQL
                         |
                         +-> Anomaly Detection
                         |
                         +-> Prometheus -> Grafana
```

## Quick start

Requirements: Docker Engine and Docker Compose.

```bash
docker compose up --build
```

Services:

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Grafana: http://localhost:3000
- PostgreSQL: localhost:5432

Default Grafana credentials for local development: `admin` / `admin`.

## Scope

Phase 1 intentionally uses simulated telemetry. No connection to real municipal systems or physical infrastructure is included.

## Roadmap

1. Telemetry foundation and simulator
2. AI-assisted anomaly reasoning and prediction
3. Digital twin and incident workflows
4. Real-world pilot integrations

## License

Apache-2.0
