# Local Development

## Prerequisites

- Docker Engine
- Docker Compose v2

## Run

```bash
git clone https://github.com/Dipak-Mehta/cityos.git
cd cityos
cp .env.example .env
docker compose up --build
```

## Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/intersections
curl http://localhost:8000/api/v1/telemetry/latest
curl http://localhost:8000/api/v1/anomalies
```

Open Grafana at `http://localhost:3000` and sign in with the local development credentials from `.env`.

## Stop

```bash
docker compose down
```

To remove local persistent data too:

```bash
docker compose down -v
```
