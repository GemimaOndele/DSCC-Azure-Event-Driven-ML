#!/usr/bin/env python3
"""Read-only smoke check of deployed endpoints. Does not upload or mutate Azure."""
import argparse
import json
import time
from urllib.request import Request, urlopen


def get_json(url):
    with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, help="Base URL of ML API")
    parser.add_argument("--functions", required=True, help="Base URL of Function App")
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-file")
    parser.add_argument("--wait", type=int, default=60)
    args = parser.parse_args()
    version = get_json(args.api.rstrip("/") + "/version")
    get_json(args.api.rstrip("/") + "/health")
    if args.expected_version and version.get("api_version") != args.expected_version:
        raise SystemExit("Unexpected deployed API release")
    deadline = time.monotonic() + args.wait
    while True:
        recent = get_json(args.functions.rstrip("/") + "/api/recent")
        rows = recent.get("results")
        if not isinstance(rows, list) or recent.get("count") != len(rows) or len(rows) > 20:
            raise SystemExit("Invalid recent schema")
        if not args.expected_file or any(row.get("fileName") == args.expected_file for row in rows):
            print(json.dumps({"api_version": version.get("api_version"),
                              "model_version": version.get("model_version"),
                              "recent_count": len(rows),
                              "expected_file_found": bool(args.expected_file)}))
            return
        if time.monotonic() >= deadline:
            raise SystemExit("Expected file not observed in time")
        time.sleep(3)


if __name__ == "__main__":
    main()
