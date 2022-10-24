registry = {
    "MockCo_Sensor-1": {
        "attributes": {"make": "MockCo", "model": "Sensor-1",},
        "variables": {
            "time": {"shape": ["time"], "attributes": {"long_name": "Time"},},
            "latitude": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "Latitude", "units": "degrees_north"},
            },
            "longitude": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "Longitude", "units": "degrees_east"},
            },
            "altitude": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "Altitude", "units": "m"},
            },
            "temperature": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "Temperature", "units": "degree_C"},
            },
            "rh": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "RH", "units": "percent"},
            },
            "wind_speed": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "Wind Speeed", "units": "m s-1"},
            },
            "wind_direction": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "Wind Direction", "units": "degree"},
            },
        },
    },
    "MockCo_Sensor-2": {
        "attributes": {"make": "MockCo", "model": "Sensor-2",},
        "variables": {
            "time": {"shape": ["time"], "attributes": {"long_name": "Time"},},
            "diameter": {
                "type": "double",
                "shape": ["bins"],
                "attributes": {"long_name": "Diameter", "units": "micron"},
            },
            "temperature": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "Temperature", "units": "degree_C"},
            },
            "rh": {
                "type": "double",
                "shape": ["time"],
                "attributes": {"long_name": "RH", "units": "percent"},
            },
            "bin_counts": {
                "type": "int",
                "shape": ["time", "bins"],
                "attributes": {"long_name": "Bin Counts", "units": "count",},
            },
        },
    },
}

