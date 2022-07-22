# mock-sensor

Python code to mock real sensor data and send it to an MQTT broker in CloudEvent format.

## Configuration

The application is configurable using environmental variables prefiex with `IOT_MOCK_SENSOR_`.

* `MQTT_BROKER` - MQTT broker host
* `MQTT_PORT` - MQTT broker port
* `MQTT_TOPIC_PREFIX` - The topic prefix to use for data, defaults to `aws-id`. Data is sent to `{MQTT_TOPIC_PREFIX}/{source-type}/data`.
* `DRY_RUN` - Setting to `true` will only generate the MQTT messages but not send them

## Data Format

JSON data on MQTT Broker can be data-only or include metadata about a station-sensor. Metadata is used downstream to update a registry of stations and sensors. Since the final data format is a CloudEvent, there is a cloud event header added as well.

### Cloud-event Header

```json
{
    "attributes": {
        "specversion": "1.0",
        "id": "58dec138-b343-40fe-a316-156524487167",
        "source": "/sensor/MockCo/Sensor-1/6789",
        "type": "gov.noaa.pmel.acg.data.insert.envds.v2",
        "datacontenttype": "application/json; charset=utf-8",
        "time": "2022-07-19T18:35:50.101472+00:00"
    }
}
```

### Data-only payload

```json
{
    [cloud_event_header],
    "data": {
        "time": "2022-07-19T17:33:00Z",
        "temperature": 23.261,
    }
}
```

### Metadata-only payload

The metadata format is [metadata-only NCO-JSON](https://www.essoar.org/doi/pdf/10.1002/essoar.10500689.1) and can include key:value attributes about the station-sensor or the variable feed. The keys of the "variables" object should match the keys in the data object for the same variable.

```json
{
    [cloud_event_header],
    "metadata": {
        "attributes": {
            "make": "MockCo",
            "model": "Sensor-1",
            "serial": "Sensor-1"
        },
        "variables": {
            "temperature": {
                "attributes": {
                    "units": "degree_C"
                }
            }
        }
    }
}
```

### Data and Metadata

```json
{
    [cloud_event_header],
    "data": {
        "time": "2022-07-19T17:33:00Z",
        "temperature": 23.261,
    },
    "metadata": {
        "attributes": {
            "make": "MockCo",
            "model": "Sensor-1",
            "serial": "Sensor-1"
        },
        "variables": {
            "temperature": {
                "attributes": {
                    "units": "degree_C"
                }
            }
        }
    }
}
```

## Deployment

### Local

```shell
$ python apps/mock-sensor/mock_sensor.py

at=INFO msg="Starting data_loop" mock_type=TestSensor1D sn=1234 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor1D sn=2345 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor1D sn=3456 data_rate=5
at=INFO msg="Starting data_loop" mock_type=TestSensor2D sn=4567 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor2D sn=5678 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor2D sn=6789 data_rate=5
at=INFO msg=Published topic=aws-id/acg-daq/data source=/sensor/MockCo/Sensor-2/6789 time=2022-06-28T19:55:45Z diameter="[0.1, 0.2, 0.35, 0.5, 0.75, 1.0]" temperature=23.473 rh=55.737 bin_counts="[10, 13, 24, 19, 13, 6]"
at=INFO msg=Published topic=aws-id/acg-daq/data source=/sensor/MockCo/Sensor-1/3456 time=2022-06-28T19:55:45Z latitude=10.022 longitude=-150.022 altitude=106.628 temperature=26.984 rh=62.495 wind_speed=7.953 wind_direction=108.663
...
```

### Local K3D Cluster

```shell
# From project root
$ make deploy-mock-sensor
$ kubectl logs -f mock-sensor

at=INFO msg="Starting data_loop" mock_type=TestSensor1D sn=1234 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor1D sn=2345 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor1D sn=3456 data_rate=5
at=INFO msg="Starting data_loop" mock_type=TestSensor2D sn=4567 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor2D sn=5678 data_rate=30
at=INFO msg="Starting data_loop" mock_type=TestSensor2D sn=6789 data_rate=5
at=INFO msg=Published topic=aws-id/acg-daq/data source=/sensor/MockCo/Sensor-2/6789 time=2022-06-28T19:55:45Z diameter="[0.1, 0.2, 0.35, 0.5, 0.75, 1.0]" temperature=23.473 rh=55.737 bin_counts="[10, 13, 24, 19, 13, 6]"
at=INFO msg=Published topic=aws-id/acg-daq/data source=/sensor/MockCo/Sensor-1/3456 time=2022-06-28T19:55:45Z latitude=10.022 longitude=-150.022 altitude=106.628 temperature=26.984 rh=62.495 wind_speed=7.953 wind_direction=108.663
...
```
