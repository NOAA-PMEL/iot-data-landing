# mock-sensor

Python code to mock real sensor data and send it to an MQTT broker

## Configuration

The application is configurable using environmental variables prefiex with `IOT_MOCK_SENSOR_`.

* `MQTT_BROKER` - MQTT broker host
* `MQTT_PORT` - MQTT broker port
* `MQTT_TOPIC_PREFIX` - The topic prefix to use for data, defaults to `instrument/data`. Data is sent to `$MQTT_TOPIC_PREFIX/{serial_number}`
* `DRY_RUN` - Setting to `true` will only generate the MQTT messages but not send them

## Deployment

###  Local

```shell
$ python apps/mock-sensor/mock_sensor.py

at=INFO msg="start run" sn=1234 data_rate=30 topic=instrument/data/1234
at=INFO msg="start run" sn=2345 data_rate=30 topic=instrument/data/2345
at=INFO msg="start run" sn=3456 data_rate=5 topic=instrument/data/3456
at=INFO msg="start run" sn=3234 data_rate=30 topic=instrument/data/3234
at=INFO msg="start run" sn=3345 data_rate=30 topic=instrument/data/3345
at=INFO msg="start run" sn=3456 data_rate=5 topic=instrument/data/3456
at=INFO msg="Data sent" sn=3456 data_rate=5 topic=instrument/data/3456 time=2022-06-28T15:45:25Z diameter="[0.1, 0.2, 0.35, 0.5, 0.75, 1.0]" temperature=26.047 rh=59.485 bin_counts="[8, 16, 23, 19, 10, 3]"
at=INFO msg="Data sent" sn=3456 data_rate=5 topic=instrument/data/3456 time=2022-06-28T15:45:25Z latitude=9.928 longitude=-149.957 altitude=100.944 temperature=25.131 rh=55.514 wind_speed=9.838 wind_direction=88.211
```

### Local K3D Cluster

```shell
# From project root
$ make deploy-mock-sensor
$ kubectl logs -f mock-sensor

at=INFO msg="start run" sn=1234 data_rate=30 topic=instrument/data/1234
at=INFO msg="start run" sn=2345 data_rate=30 topic=instrument/data/2345
at=INFO msg="start run" sn=3456 data_rate=5 topic=instrument/data/3456
at=INFO msg="start run" sn=3234 data_rate=30 topic=instrument/data/3234
at=INFO msg="start run" sn=3345 data_rate=30 topic=instrument/data/3345
at=INFO msg="start run" sn=3456 data_rate=5 topic=instrument/data/3456
at=INFO msg="Data sent" sn=3456 data_rate=5 topic=instrument/data/3456 time=2022-06-28T15:45:25Z diameter="[0.1, 0.2, 0.35, 0.5, 0.75, 1.0]" temperature=26.047 rh=59.485 bin_counts="[8, 16, 23, 19, 10, 3]"
at=INFO msg="Data sent" sn=3456 data_rate=5 topic=instrument/data/3456 time=2022-06-28T15:45:25Z latitude=9.928 longitude=-149.957 altitude=100.944 temperature=25.131 rh=55.514 wind_speed=9.838 wind_direction=88.211
```
