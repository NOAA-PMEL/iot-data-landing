# IoT MockSensor output

Below are examples of possible sensor output. These are json representations of the MQTT payload created using the CloudEvents spec. The first is the data only while the second includes a metadata portion that could be used to register the sensor at some point. 

The current version of the MockSensor connects to a simple MQTT broker (Mosquitto) without TLS. My plan is to add functionality:
 - allow for TLS connections
 - allow for payload encryption
 - integrate with AWS IoT broker

For now, this is a starting point for the payload and we can modify as necessary. 

### Payload: Data only
```
{
    "attributes": {
        "type": "gov.noaa.pmel.acg.data.insert.envds.v2",
        "source": "/sensor/MockCo/Sensor_1/1234",
        "datacontenttype": "application/json; charset=utf-8",
        "specversion": "1.0",
        "id": "051eba76-f4bd-443e-b209-8bea5a497377",
        "time": "2022-04-01T22:36:50.001213+00:00"
    },
    "data": {
        "data": {
            "time": "2022-04-01T22:36:50Z",
            "latitude": 9.906,
            "longitude": -150.028,
            "altitude": 91.899,
            "temperature": 27.166,
            "rh": 61.317,
            "wind_speed": 7.282,
            "wind_dir": 104.854
        }
    }
}
```

### Payload: Data with metadata
```
{
    "attributes": {
        "type": "gov.noaa.pmel.acg.data.insert.envds.v2",
        "source": "/sensor/MockCo/Sensor_1/1234",
        "datacontenttype": "application/json; charset=utf-8",
        "specversion": "1.0",
        "id": "17d23319-4b10-4578-afc6-878c75081b11",
        "time": "2022-04-02T16:39:53.003270+00:00"
    },
    "data": {
        "data": {
            "time": "2022-04-02T16:39:53Z",
            "latitude": 9.927,
            "longitude": -150.044,
            "altitude": 99.707,
            "temperature": 24.634,
            "rh": 57.185,
            "wind_speed": 5.474,
            "wind_dir": 81.401
        },
        "metadata": {
            "make": "MockCo",
            "model": "Sensor_1",
            "variables": {
                "time": {
                    "long_name": "Time",
                    "dimension": [
                        "time"
                    ]
                },
                "latitude": {
                    "long_name": "Latitude",
                    "data_type": "double",
                    "units": "degrees_north",
                    "dimension": [
                        "time"
                    ]
                },
                "longitude": {
                    "long_name": "Longitude",
                    "data_type": "double",
                    "units": "degrees_east",
                    "dimension": [
                        "time"
                    ]
                },
                "altitude": {
                    "long_name": "Altitude",
                    "data_type": "double",
                    "units": "m"
                },
                "temperature": {
                    "long_name": "Temperature",
                    "data_type": "double",
                    "units": "degree_C",
                    "dimension": [
                        "time"
                    ]
                },
                "rh": {
                    "long_name": "RH",
                    "data_type": "double",
                    "units": "percent"
                },
                "wind_speed": {
                    "long_name": "Wind Speed",
                    "data_type": "double",
                    "units": "m s-1",
                    "dimension": [
                        "time"
                    ]
                },
                "wind_direction": {
                    "long_name": "Wind Direction",
                    "data_type": "double",
                    "units": "degree",
                    "dimension": [
                        "time"
                    ]
                }
            }
        }
    }
}
```