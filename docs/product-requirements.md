# CITYOS Phase 1 — Product Requirements

## Goal

Build a local MVP that continuously simulates traffic-intersection telemetry, stores it, exposes it through an API, and identifies basic infrastructure risk.

## User

An infrastructure operator who needs a single view of asset health and recent telemetry.

## Phase 1 features

1. Three simulated intersections.
2. Telemetry every five seconds by default.
3. Persistent PostgreSQL storage.
4. API health endpoint.
5. Latest telemetry endpoint.
6. Intersection inventory endpoint.
7. Rule-based anomaly/risk classification.
8. Prometheus metrics and Grafana visualization.
9. Repeatable failure simulation for demos.

## Non-goals

- Real municipal integrations
- Automated control of traffic signals
- Production AI predictions
- Facial recognition or personal-data processing
- Autonomous safety-critical decisions

## Success criteria

After `docker compose up --build`, telemetry should continuously arrive, the API should report healthy, and Grafana should display API telemetry metrics.
