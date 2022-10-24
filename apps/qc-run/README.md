# qc-run

An application to receive Knative CloudEvent messages, parse them, run QC checks on them, and publish the data back to a Knative Kafka broker with a different `type`.

## Naming Convention

Given the following CloudEvent

```json
{
    "attributes": {
        "specversion": "1.0",
        "id": "1aabae46-d42d-4016-b509-428cc92a0634",
        "source": "/sensor/MockCo/Sensor-2/3456",
        "type": "gov.noaa.pmel.acg.data.insert.envds.v2",
        "datacontenttype": "application/json; charset=utf-8",
        "time": "2022-06-28T15: 56: 25.003173+00: 00"
    },
    "data": {
        "metadata": {},
        "data": {
            "time": "2022-06-28T15:56:25Z",
            "temperature": 26.676,
            "rh": 55.685
        }
    }
}
```

The `source` field is parsed into the following:

* `make` - MockCo
* `model` - Sensor-2
* `serial` - 3456
* `thing_id` - **MockCo_Sensor-2_QC** - This must already exist as a dataset in ERDDAP before data will be added to ERDDAP.

## Configuration

The application is configurable using environmental variables prefixed with `IOT_ERDDAP_INSERT_`.

* `HOST` - The host to run the service, defaults to `0.0.0.0`.
* `PORT` - The port to run the service, defaults to `8789`.
* `DEBUG` - Passed on through to Flask's `run` method for the applications, do not use in production.
* `S3_USER` - An S3 API `ACCESS_KEY`.
* `S3_PASS` - An S3 API `SECRET_ACCESS_KEY`.
* `S3_BUCKET` - S3 bucket to upload QCed parquet files into, defaults to `iot-data-landing`.
* `S3_PATH` - Relative path to upload QCed parquet files into, i.e. `[bucket]/[path]/[file]`. Defaults to `data`.
* `S3_ENDPOINT` - URL endpoint to an S3 API, defaults to `http://minio:9000`.
* `S3_REGION` - Region of the S3 API Bucket, defaults to `''`.
* `KNATIVE_BROKER` - URL to a running Knative Broker, defaults to `http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default`.
* `DRY_RUN` - If set to `true` will not POST messages to ERDDAP and only log what would be sent.

## Deployment

### Local

```shell
$ IOT_QC_RUN_DEBUG=yes python apps/qc-run/qc_run.py
 * Serving Flask app 'qc_run' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
at=INFO msg=" * Running on all addresses (0.0.0.0)\n   WARNING: This is a development server. Do not use it in a production deployment.\n * Running on http://127.0.0.1:8789\n * Running on http://192.168.1.171:8789 (Press CTRL+C to quit)"
```

```shell
$ http POST http://localhost:8789 data='{"attributes": {"specversion": "1.0", "id": "58dec138-b343-40fe-a316-156524487167", "source": "/sensor/MockCo/Sensor-2/6789", "type": "gov.noaa.pmel.acg.data.insert.envds.v2", "datacontenttype": "application/json; charset=utf-8", "time": "2022-07-19T18:35:50.101472+00:00"}, "data": {"metadata": {}, "data": {"time": "2022-07-19T18:35:50Z", "diameter": [0.1, 0.2, 0.35, 0.5, 0.75, 1.0], "temperature": 23.852, "rh": 56.033, "bin_counts": [8, 16, 26, 21, 12, 5]}}}' specversion=1.0 source=/sensor/MockCo/Sensor-2/6789 type=gov.noaa.pmel.acg.data.insert.envds.v2 id=boo
HTTP/1.1 200 OK
Connection: close
Content-Length: 79
Content-Type: text/html; charset=utf-8
Date: Fri, 14 Oct 2022 17:43:55 GMT
Server: Werkzeug/2.1.2 Python/3.9.12

Uploaded 6 results to MockCo_Sensor-2_S20220719T183550Z_E20220719T183550Z.jsonl
```

### Local K3D Cluster

This deploys the application as a Knative service and a Trigger that filters all messages with a `type` of `gov.noaa.pmel.acg.data.insert.envds.v2` and sends them to this application. The filter is configurable in the `qc-run.yaml` file.

```shell
# From project root
$ make deploy-qc-run
# You must find the knative pod to view the logs
$ kubectl get pod
# Find the qc-run pod
$ kubectl logs -f qc-run-00001-deployment-5bf4bf57b6-p4hkk user-container

at=INFO msg="Uploaded 6 results to MockCo_Sensor-2_S20221024T201300Z_E20221024T201300Z.jsonl"
at=INFO msg="Uploaded 1 results to MockCo_Sensor-1_S20221024T201300Z_E20221024T201300Z.jsonl"
at=INFO msg="Uploaded 6 results to MockCo_Sensor-2_S20221024T201300Z_E20221024T201300Z.jsonl"
at=INFO msg="Uploaded 1 results to MockCo_Sensor-1_S20221024T201300Z_E20221024T201300Z.jsonl
```
