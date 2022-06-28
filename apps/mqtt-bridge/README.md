# MQTT Bridge

This app is the glue between any MQTT broker and Knative. The app subscribes to an MQTT Broker/Port/Topic for JSON messages, converts them to CloudEvents, and publishes them to a Knative service URL.

## Configuration

The application is configurable using environmental variables prefiex with `MQTT_BRIDGE_`.

* `MQTT_BROKER` - MQTT broker host
* `MQTT_PORT` - MQTT broker port
* `MQTT_TOPIC_FILTER` - An MQTT filter to use to filter messages, defaults to `'instrument/data/+'` to process one level of serial numbers.
* `MQTT_TOPIC_SUBSCRIPTION` - An MQTT subscription string, defaults to `instrument/#` to capture all instrument data.
* `DRY_RUN` - Setting to `true` will only listen on the MQTT broker and will not publish messages to the Knative service URL. This is useful when running locally and not in a K3D cluster as the Knative service URL isn't available outside of the cluster.

## Deployment

### Local

```shell
$ MQTT_BRIDGE_DRY_RUN=yes python apps/mqtt-bridge/mqtt_bridge.py

at=INFO msg=Starting mqtt_broker=localhost mqtt_port=1883 mqtt_topic_filter=instrument/data/+ mqtt_topic_subscription=instrument/# mqtt_client_id=fd75b60c0b3c4be9b533c29de55a48fc knative_broker=http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default dry_run=false
at=INFO msg=Subscribed mqtt_broker=localhost mqtt_port=1883 mqtt_topic_filter=instrument/data/+ mqtt_topic_subscription=instrument/# mqtt_client_id=fd75b60c0b3c4be9b533c29de55a48fc
at=INFO msg="{'attributes': {'specversion': '1.0', 'id': '208e5d4b-9f08-4929-ad84-5c98d5c9a51f', 'source': '/sensor/MockCo/Sensor-2/3456', 'type': 'gov.noaa.pmel.acg.data.insert.envds.v2', 'datacontenttype': 'application/json; charset=utf-8', 'time': '2022-06-28T15:54:50.002710+00:00'}, 'data': {'data': {'time': '2022-06-28T15:54:50Z', 'diameter': [0.1, 0.2, 0.35, 0.5, 0.75, 1.0], 'temperature': 22.349, 'rh': 55.709, 'bin_counts': [11, 14, 26, 21, 12, 4]}}}" topic_filter=instrument/data/+ subscription=instrument/#
```

### Local K3D cluster

```shell
# From project root
$ make deploy-mqtt-bridge
$ kubectl logs -f mqtt-bridge

at=INFO msg="{'attributes': {'specversion': '1.0', 'id': 'eb660d87-26f6-4d96-a47e-05dbd521e691', 'source': '/sensor/MockCo/Sensor-1/3456', 'type': 'gov.noaa.pmel.acg.data.insert.envds.v2', 'datacontenttype': 'application/json; charset=utf-8', 'time': '2022-06-28T03:45:05.002060+00:00'}, 'data': {'data': {'time': '2022-06-28T03:45:05Z', 'latitude': 9.97, 'longitude': -149.954, 'altitude': 107.896, 'temperature': 25.457, 'rh': 59.284, 'wind_speed': 10.402, 'wind_direction': 82.255}}}" topic_filter=instrument/data/+ subscription=instrument/#
```
