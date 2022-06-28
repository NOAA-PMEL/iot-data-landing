import abc
import time
import math
import random
import asyncio
import logging
from datetime import datetime

from logfmter import Logfmter
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes
from cloudevents.http import CloudEvent, to_structured

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger('mock_sensor')
L.setLevel(logging.INFO)


def time_to_next(sec):
    now = time.time()
    delta = sec - (math.fmod(now, sec))
    return delta


class MockSensor(abc.ABC):

    isofmt = "%Y-%m-%dT%H:%M:%SZ"

    def __init__(
        self,
        sn: str,
        mqtt_client,
        mqtt_topic_prefix,
        data_rate: int = 30,
    ) -> None:

        L.debug("Starting %s", self.__class__.__name__)

        # handle arguments
        self.sn = sn
        self.mqtt_client = mqtt_client
        self.mqtt_topic = f'{mqtt_topic_prefix}/{sn}'
        self.data_rate = data_rate

        self.extra = {
            'sn': self.sn,
            'data_rate': self.data_rate,
            'topic': self.mqtt_topic
        }
        # self.mqtt_host = mqtt_host
        # self.mqtt_port = mqtt_port
        # self.mqtt_tls_cert = mqtt_tls_cert

        # define data queues
        self.data_buffer = asyncio.Queue()
        self.payload_buffer = asyncio.Queue()
        self.send_buffer = asyncio.Queue()

        # run flag
        self.doRun = False

        self.task_list = []

    @abc.abstractmethod
    def get_metadata(self):
        pass

    def start(self):
        asyncio.get_running_loop().create_task(self.run())

    async def run(self):
        self.doRun = True

        L.info("start run", extra=self.extra)

        # start loops
        self.task_list.append(asyncio.get_running_loop().create_task(self.data_loop()))
        asyncio.get_running_loop().create_task(self.ce_loop())
        asyncio.get_running_loop().create_task(self.send_loop())

        while self.doRun:
            await asyncio.sleep(1)

        # this only shuts down the data_loop to allow last message(s) to go through
        for task in self.task_list:
            task.cancel()

        L.info("shutdown", extra=self.extra)

    # derived classes define how data is created
    @abc.abstractmethod
    async def data_loop(self):
        pass

    # package data into cloudevent
    async def ce_loop(self):

        # define type and source here
        sensor_make = self.get_metadata()["attributes"]["make"]
        sensor_model = self.get_metadata()["attributes"]["model"]
        attributes = {
            "type": f"gov.noaa.pmel.acg.data.insert.envds.v2",
            "source": f"/sensor/{sensor_make}/{sensor_model}/{self.sn}",
            "datacontenttype": "application/json; charset=utf-8",
        }

        # get data from queue, package into cloudevent, send via mqtt
        while True:
            data = await self.data_buffer.get()
            # payload = {"data": data, "metadata": self.get_metadata()}
            payload = {"data": data}
            ce = CloudEvent(attributes=attributes, data=payload)
            L.debug(f"ce_loop: cloudevent = {ce}", extra=self.extra)
            await self.send_buffer.put(ce)

            await asyncio.sleep(0.1)

    # outpu to mqtt broker using paho client
    async def send_loop(self):

        properties = Properties(PacketTypes.PUBLISH)
        properties.ContentType = "application/cloudevents+json; charset=utf-8"

        while True:
            event = await self.send_buffer.get()
            headers, body = to_structured(event)
            # print(headers, body)
            ret = self.mqtt_client.publish(
                self.mqtt_topic, payload=body, qos=0, properties=properties
            )
            await asyncio.sleep(0.1)

    def shutdown(self):
        self.doRun = False


class TestSensor1D(MockSensor):

    metadata = {
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
    }

    def get_metadata(self):
        return TestSensor1D.metadata

    async def data_loop(self):

        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        L.debug("Starting data_loop", extra=self.extra)
        await asyncio.sleep(time_to_next(self.data_rate))
        while True:
            data = dict()

            dt = datetime.utcnow()
            dt_str = datetime.strftime(dt, MockSensor.isofmt)
            # print(f"dt(hour:min): {dt.hour}:{dt.minute}")
            data["time"] = dt_str
            data["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
            data["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
            data["altitude"] = round(100 + random.uniform(-10, 10), 3)

            data["temperature"] = round(25 + random.uniform(-3, 3), 3)
            data["rh"] = round(60 + random.uniform(-5, 5), 3)
            data["wind_speed"] = round(10 + random.uniform(-5, 5), 3)
            data["wind_direction"] = round(90 + random.uniform(-20, 20), 3)

            await self.data_buffer.put(data)
            L.info(f"Data sent", extra={**self.extra, **data})
            await asyncio.sleep(time_to_next(self.data_rate))


class TestSensor2D(MockSensor):

    metadata = {
        "attributes": {"make": "MockCo", "model": "Sensor-2",},
        "variables": {
            "time": {"shape": ["time"], "attributes": {"long_name": "Time"},},
            "diameter": {
                "type": "double",
                "shape": ["bins"],
                "attributes": {
                    "long_name": "Diameter",
                    "units": "micron"
                }
            },
            # "latitude": {
            #     "type": "double",
            #     "shape": ["time"],
            #     "attributes": {"long_name": "Latitude", "units": "degrees_north"},
            # },
            # "longitude": {
            #     "type": "double",
            #     "shape": ["time"],
            #     "attributes": {"long_name": "Longitude", "units": "degrees_east"},
            # },
            # "altitude": {
            #     "type": "double",
            #     "shape": ["time"],
            #     "attributes": {"long_name": "Altitude", "units": "m"},
            # },
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
                "attributes": {
                    "long_name": "Bin Counts",
                    "units": "count",
                }
            },
        },
    }

    def get_metadata(self):
        return TestSensor2D.metadata

    async def data_loop(self):

        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        L.debug("Starting data_loop", extra=self.extra)
        await asyncio.sleep(time_to_next(self.data_rate))
        while True:
            data = dict()

            dt = datetime.utcnow()
            dt_str = datetime.strftime(dt, MockSensor.isofmt)
            # print(f"dt(hour:min): {dt.hour}:{dt.minute}")
            data["time"] = dt_str
            data["diameter"] = [0.1, 0.2, 0.35, 0.5, 0.75, 1.0]
            # data["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
            # data["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
            # data["altitude"] = round(100 + random.uniform(-10, 10), 3)

            data["temperature"] = round(25 + random.uniform(-3, 3), 3)
            data["rh"] = round(60 + random.uniform(-5, 5), 3)

            base_count = [10, 15, 25, 20, 12, 5]
            count = []
            for bc in base_count:
                count.append(int(bc + random.uniform(-2, 2)))
            data["bin_counts"] = count

            await self.data_buffer.put(data)
            L.info(f"Data sent", extra={**self.extra, **data})
            await asyncio.sleep(time_to_next(self.data_rate))
