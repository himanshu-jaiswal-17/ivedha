#!/usr/bin/env python3
# Simple REST service to push service status data into Elasticsearch
# and retrieve it via healthcheck endpoints.
#
# Endpoints:
#   POST /add                      - index a service status doc
#   GET  /healthcheck              - get all services + overall app status
#   GET  /healthcheck/<service>    - get status of one service

import os
import json
import sys
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

# can be overridden with env vars
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "rbcapp1-services")
ES_USER = os.getenv("ES_USER", "")
ES_PASS = os.getenv("ES_PASS", "")

app = Flask(__name__)


def get_es_client():
    kwargs = {"hosts": [ES_HOST]}
    if ES_USER and ES_PASS:
        kwargs["basic_auth"] = (ES_USER, ES_PASS)
    return Elasticsearch(**kwargs)


def ensure_index_exists(es):
    """Creates the index with keyword mappings if it doesn't exist yet."""
    try:
        if not es.indices.exists(index=ES_INDEX):
            es.indices.create(index=ES_INDEX, body={
                "mappings": {
                    "properties": {
                        "service_name":       {"type": "keyword"},
                        "service_status":     {"type": "keyword"},
                        "host_name":          {"type": "keyword"},
                        "application_name":   {"type": "keyword"},
                        "application_status": {"type": "keyword"},
                        "timestamp":          {"type": "date"}
                    }
                }
            })
            print(f"[INFO] Created index: {ES_INDEX}", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] Index creation: {e}", file=sys.stderr)


@app.route("/add", methods=["POST"])
def add_status():
    """Accepts JSON body or file upload and indexes it into ES."""
    try:
        # support both file upload and raw json
        if "file" in request.files:
            file = request.files["file"]
            data = json.loads(file.read().decode("utf-8"))
        elif request.is_json:
            data = request.get_json()
        else:
            return jsonify({"error": "No JSON payload or file provided"}), 400

        # auto-add timestamp if missing
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        es = get_es_client()
        ensure_index_exists(es)
        result = es.index(index=ES_INDEX, body=data)

        return jsonify({
            "message": "Document indexed successfully",
            "id": result["_id"],
            "result": result["result"]
        }), 201

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        print(f"[ERROR] POST /add: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


@app.route("/healthcheck", methods=["GET"])
def healthcheck_all():
    """Returns overall rbcapp1 status + latest status of each service."""
    try:
        es = get_es_client()

        if not es.indices.exists(index=ES_INDEX):
            return jsonify({
                "application_name": "rbcapp1",
                "application_status": "UNKNOWN",
                "services": [],
                "message": "No data yet. POST to /add first."
            }), 200

        # get latest doc per service using terms + top_hits agg
        result = es.search(index=ES_INDEX, body={
            "size": 0,
            "aggs": {
                "services": {
                    "terms": {"field": "service_name", "size": 100},
                    "aggs": {
                        "latest": {
                            "top_hits": {
                                "size": 1,
                                "sort": [{"timestamp": {"order": "desc"}}]
                            }
                        }
                    }
                }
            }
        })

        buckets = result["aggregations"]["services"]["buckets"]
        services = []
        overall_status = "UP"

        for bucket in buckets:
            hit = bucket["latest"]["hits"]["hits"][0]["_source"]
            services.append({
                "service_name": hit.get("service_name"),
                "service_status": hit.get("service_status"),
                "host_name": hit.get("host_name"),
                "timestamp": hit.get("timestamp")
            })
            if hit.get("service_status") == "DOWN":
                overall_status = "DOWN"

        return jsonify({
            "application_name": "rbcapp1",
            "application_status": overall_status,
            "services": services
        }), 200

    except Exception as e:
        print(f"[ERROR] GET /healthcheck: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


@app.route("/healthcheck/<service_name>", methods=["GET"])
def healthcheck_service(service_name):
    """Returns latest status for a specific service."""
    try:
        es = get_es_client()

        result = es.search(index=ES_INDEX, body={
            "size": 1,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {"term": {"service_name": service_name}}
        })

        hits = result["hits"]["hits"]
        if not hits:
            return jsonify({"error": f"No data found for service: {service_name}"}), 404

        source = hits[0]["_source"]
        return jsonify({
            "service_name": source.get("service_name"),
            "service_status": source.get("service_status"),
            "host_name": source.get("host_name"),
            "timestamp": source.get("timestamp")
        }), 200

    except Exception as e:
        print(f"[ERROR] GET /healthcheck/{service_name}: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"[INFO] Connecting to Elasticsearch at {ES_HOST}", file=sys.stderr)
    app.run(host="0.0.0.0", port=5000, debug=True)
