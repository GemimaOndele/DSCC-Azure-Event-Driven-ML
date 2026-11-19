# DSCC-Azure-Event-Driven-ML
Event-driven Telecom Customer Churn prediction pipeline on Microsoft Azure, featuring serverless computing, distributed systems, observability and CI/CD.

## ML model and API

The versioned model is trained locally with `py -3.12 model\train.py`. To run
the inference API, install `api\requirements-dev.txt` and start it with
`py -3.12 -m uvicorn api.main:app --reload`. API tests run with
`py -3.12 -m pytest api\tests`.

The API serves the versioned ONNX export and exposes `GET /health`, `GET /version`, `POST /predict`, and
`GET /metrics`. Build its multi-stage container from the repository root with
`docker build -f api\Dockerfile -t churn-ml-api:1.0.0 .`. Set
`APPLICATIONINSIGHTS_CONNECTION_STRING` to enable Azure Monitor OpenTelemetry.
