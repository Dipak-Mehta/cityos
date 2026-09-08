import os
import random
import time
from datetime import datetime, timezone

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
INTERVAL = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "5"))

INTERSECTIONS = ["PUN-001", "PUN-002", "PUN-003"]


def telemetry(intersection_id: str, failure: bool = False):
    if failure:
        return {
            "intersection_id": intersection_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "traffic_volume": random.randint(1200, 1600),
            "signal_latency": round(random.uniform(3.2, 5.0), 2),
            "power_voltage": round(random.uniform(195, 208), 1),
            "error_count": random.randint(10, 25),
        }
    return {
        "intersection_id": intersection_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "traffic_volume": random.randint(500, 1000),
        "signal_latency": round(random.uniform(0.8, 1.8), 2),
        "power_voltage": round(random.uniform(225, 240), 1),
        "error_count": random.randint(0, 2),
    }


def main():
    cycle = 0
    print(f"CITYOS simulator started; API={API_URL}")
    while True:
        cycle += 1
        for intersection_id in INTERSECTIONS:
            # Every 30 cycles, simulate a short high-risk event at PUN-003.
            failure = intersection_id == "PUN-003" and 30 <= cycle % 60 <= 36
            payload = telemetry(intersection_id, failure=failure)
            try:
                response = requests.post(f"{API_URL}/api/v1/telemetry", json=payload, timeout=5)
                response.raise_for_status()
                print(intersection_id, "FAILURE-SCENARIO" if failure else "normal", response.status_code)
            except requests.RequestException as exc:
                print("API unavailable:", exc)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
