"""DSCC pipeline — one Python 3.12 Function App, v2 programming model.

Functions:
  * dispatcher : Event Grid BlobCreated on input/ -> queue inference-requests
  * worker     : queue trigger -> POST /predict/batch -> output/ + Cosmos/Table
  * recent     : GET /api/recent -> last 20 results for the static dashboard
"""

from __future__ import annotations

import json
import logging

import azure.functions as func

from src import service
from src.azure_clients import get_clients

LOGGER = logging.getLogger("dscc.pipeline")

app = func.FunctionApp()


@app.event_grid_trigger(arg_name="event")
def dispatcher(event: func.EventGridEvent) -> None:
    settings, blobs, queue, _api, _results = get_clients()
    result = service.dispatch(
        event.get_json(), settings=settings, blobs=blobs, queue=queue
    )
    LOGGER.info("dispatcher result", extra=result)


@app.queue_trigger(
    arg_name="message",
    queue_name="inference-requests",
    connection="AzureWebJobsStorage",
)
def worker(message: func.QueueMessage) -> None:
    settings, blobs, _queue, api, results = get_clients()
    # Transient errors must escape so the host retries up to maxDequeueCount=5,
    # after which the message lands in inference-requests-poison.
    service.process(
        message.get_body().decode("utf-8"),
        settings=settings,
        blobs=blobs,
        api=api,
        results=results,
    )


@app.function_name(name="recent")
@app.route(route="recent", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def recent(request: func.HttpRequest) -> func.HttpResponse:
    settings, _blobs, _queue, _api, results = get_clients()
    payload, allowed_origin = service.recent(
        results=results,
        settings=settings,
        request_origin=request.headers.get("Origin"),
    )
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if allowed_origin:
        headers["Access-Control-Allow-Origin"] = allowed_origin
        headers["Vary"] = "Origin"
    return func.HttpResponse(
        body=json.dumps(payload, ensure_ascii=False),
        status_code=200,
        headers=headers,
    )
