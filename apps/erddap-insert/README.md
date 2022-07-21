# erddap-insert

An application to receive Knative CloudEvent messages, parse them, and publish the data to ERDDAP dataset for each unique instrument.

The `registry.py` file is a place holder for a real registry that would hold metadata for a given sensor (make/model).

This requires that for each CloudEvent coming into this application that an ERDDAP dataset of type `EDDTableFromHttpGet` exists to accept the data. The datasets are set up as make/model with subfolder for serial_number. The result is a dataset for each instrument/sensor type which can be filtered for serial_number. The actual data get saved (by ERDDAP) in `make/model/serial_number/year/dayfiles.jsonl`.

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
            "diameter": [
                0.1,
                0.2,
                0.35,
                0.5,
                0.75,
                1.0
            ],
            "temperature": 26.676,
            "rh": 55.685,
            "bin_counts": [
                8,
                16,
                25,
                18,
                11,
                4
            ]
        }
    }
}
```

The `source` field is parsed into the following:

* `make` - MockCo
* `model` - Sensor-2
* `serial` - 3456
* `thing_id` - MockCo_Sensor-2 - This must already exist as a dataset in ERDDAP before data will be added to ERDDAP.

## Configuration

The application is configurable using environmental variables prefixed with `IOT_ERDDAP_INSERT_`.

* `HOST` - The host to run the service, defaults to `0.0.0.0`.
* `PORT` - The port to run the service, defaults to `8787`.
* `DEBUG` - Passed on through to Flask's `run` method for the applications, do not use in production.
* `URL` - Base ERDDAP TableDap URL that a dataset_id should be concatenated onto, defaults to `http://localhost:8081/erddap/tabledap`. So data with a source of `/sensor/MockCo/Sensor-2/3456` would then expect the dataset to exist at `http://localhost:8081/erddap/tabledap/MockCo_Sensor-2.insert`.
* `AUTHOR` - The ERDDAP `author` that should be included in POST requets. This is setup in the ERDDAP dataset as a security measure.
* `DRY_RUN` - If set to `true` will not POST messages to ERDDAP and only log what would be sent.

## Deployment

### Local

```shell
$ IOT_ERDDAP_INSERT_DEBUG=yes python apps/erddap-insert/erddap_insert.py
 * Serving Flask app 'erddap_insert' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
at=INFO msg=" * Running on all addresses (0.0.0.0)\n   WARNING: This is a development server. Do not use it in a production deployment.\n * Running on http://127.0.0.1:8787\n * Running on http://192.168.1.171:8787 (Press CTRL+C to quit)"
```

### Local K3D Cluster

This deploys the application as a Knative service and a Trigger that filters all messages with a `type` of `gov.noaa.pmel.acg.data.insert.envds.v2` and sends them to this application. The filter is configurable in the `erddap-insert.yaml` file.

```shell
# From project root
$ make deploy-erddap-insert
# You must find the knative pod to view the logs
$ kubectl get pod
# Find the erddap-insert pod
$ kubectl logs -f erddap-insert-00015-deployment-5bf4bf57b6-p4hkk user-container

at=INFO msg="Sent POST to ERRDAP @ http://erddap:8080/erddap/tabledap/MockCo_Sensor-2.insert" make=MockCo model=Sensor-2 serial_number=3456 author=envds_secretkey time=2022-06-28T03:40:45Z diameter=%5B0.1,0.2,0.35,0.5,0.75,1.0%5D temperature=27.13 rh=56.028 bin_counts=%5B8,14,23,18,10,6%5D
at=INFO msg="Sent POST to ERRDAP @ http://erddap:8080/erddap/tabledap/MockCo_Sensor-1.insert" make=MockCo model=Sensor-1 serial_number=3456 author=envds_secretkey time=2022-06-28T03:40:45Z latitude=9.944 longitude=-150.04 altitude=94.901 temperature=23.181 rh=56.051 wind_speed=13.279 wind_direction=89.798
```
