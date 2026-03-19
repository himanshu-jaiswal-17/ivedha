#!/usr/bin/env python3
# Monitors httpd, rabbitmq and postgresql services on the local machine.
# Writes JSON status files per service.
# If any service is down, rbcapp1 is considered DOWN.

import subprocess
import socket
import json
import os
from datetime import datetime, timezone

SERVICES = ["httpd", "rabbitmq-server", "postgresql"]
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status_output")


def get_hostname():
    return socket.gethostname()


def check_service_status(service_name):
    """Uses systemctl to check if a service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "UP" if result.stdout.strip() == "active" else "DOWN"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"[WARN] Could not check service '{service_name}': {e}")
        return "DOWN"


def get_application_status(service_statuses):
    """rbcapp1 is DOWN if any dependent service is DOWN."""
    for status in service_statuses:
        if status["service_status"] == "DOWN":
            return "DOWN"
    return "UP"


def write_status_file(payload, output_dir):
    """Writes JSON to {serviceName}-status-{timestamp}.json"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    service_or_app = payload.get("service_name", payload.get("application_name", "unknown"))
    filename = f"{service_or_app}-status-{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[INFO] Written: {filepath}")
    return filepath


def main():
    hostname = get_hostname()
    service_statuses = []

    print(f"{'='*60}")
    print(f"  rbcapp1 Service Monitor - Host: {hostname}")
    print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    # check each service and write individual JSON files
    for service in SERVICES:
        status = check_service_status(service)
        payload = {
            "service_name": service,
            "service_status": status,
            "host_name": hostname
        }
        service_statuses.append(payload)
        write_status_file(payload, OUTPUT_DIR)
        print(f"  {service}: {status}")

    # overall app status
    app_status = get_application_status(service_statuses)
    app_payload = {
        "application_name": "rbcapp1",
        "application_status": app_status,
        "host_name": hostname,
        "dependent_services": service_statuses
    }
    write_status_file(app_payload, OUTPUT_DIR)

    print(f"\n  rbcapp1 Overall Status: {app_status}")
    print(f"{'='*60}")

    return app_status


if __name__ == "__main__":
    main()
