# register-thing

An application to receive Knative CloudEvent messages, parse them for things and thing metadata, and save the information to a Redis database. The Redis database acts as the "registry" of things and their metadata. Different apps provide access to that registry through different APIs.


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
        "data": {},
        "metadata": {
            "attributes": {
                "make": "MockCo",
                "model": "Sensor-2",
                "serial": "3456",
            },
            "variables": {
                "time": {
                    "shape": ["time"],
                    "attributes": {
                        "long_name": "Time"
                    }
                },
                "latitude": {
                    "type": "double",
                    "shape": ["time"],
                    "attributes": {
                        "long_name": "Latitude",
                        "units": "degrees_north"
                    }
                }
            }
        }
    }
}
```

The `source` field is parsed into the following:

* `make` - MockCo
* `model` - Sensor-2
* `serial` - 3456
* `thing_id` - MockCo_Sensor-2 - This becomings the metadata key in Redis for this metadata record.

The Redis registry will be updated with the entire `metadata` block every time it is found in a message. The Redis key will be `things:[thing_id]:metadata`

## Configuration

The application is configurable using environmental variables prefixed with `IOT_REGISTER_THING_`.

* `HOST` - The host to run the service, defaults to `0.0.0.0`.
* `PORT` - The port to run the service, defaults to `8788`.
* `DEBUG` - Passed on through to Flask's `run` method for the applications, do not use in production.
* `REDIS_URL` - Redis connection URL to use. Should include any username/password and database name.
* `DRY_RUN` - If set to `true` will not save any data to REDIS and only log what would be sent.

## Deployment

### Local

```shell
# Start a redis container locally
$ docker run --net=host redis
$ IOT_REGISTER_THING_DEBUG=yes python apps/register-thing/register_thing.py
 * Serving Flask app 'register_thing' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
at=INFO msg=" * Running on all addresses (0.0.0.0)\n   WARNING: This is a development server. Do not use it in a production deployment.\n * Running on http://127.0.0.1:8788\n * Running on http://192.168.1.171:8788 (Press CTRL+C to quit)"
```

You can send a local example request like so:

```shell
$ http POST http://localhost:8788 \
    data=' { "attributes": { "specversion": "1.0", "id": "1aabae46-d42d-4016-b509-428cc92a0634", "source": "/sensor/MockCo/Sensor-2/3456", "type": "gov.noaa.pmel.acg.data.insert.envds.v2", "datacontenttype": "application/json; charset=utf-8", "time": "2022-06-28T15: 56: 25.003173+00: 00" }, "data": { "metadata": { "attributes": { "make": "MockCo", "model": "Sensor-2", "serial": "3456" }, "variables": { "time": { "shape": [ "time" ], "attributes": { "long_name": "Time" } }, "latitude": { "type": "double", "shape": [ "time" ], "attributes": { "long_name": "Latitude", "units": "degrees_north" } } } } }}' \
    specversion=1.0 \
    source=/sensor/MockCo/Sensor-2/6789 \
    type=gov.noaa.pmel.acg.data.insert.envds.v2 \
    id=boo
```

### Local K3D Cluster

This deploys the application as a Knative service and a Trigger that filters all messages with a `type` of `gov.noaa.pmel.acg.data.insert.envds.v2` and sends them to this application. The filter is configurable in the `register-thing.yaml` file.

```shell
# From project root
$ make deploy-register-thing
# You must find the knative pod to view the logs
$ kubectl get pod
# Find the register-thing pod
$ kubectl logs -f register-thing-00001-deployment-5ff77b8c96-p5pm5 user-container
[2022-07-19 16:12:06 +0000] [1] [INFO] Starting gunicorn 20.1.0
[2022-07-19 16:12:06 +0000] [1] [INFO] Listening at: http://0.0.0.0:8080 (1)
[2022-07-19 16:12:06 +0000] [1] [INFO] Using worker: gthread
[2022-07-19 16:12:06 +0000] [7] [INFO] Booting worker with pid: 7
```
