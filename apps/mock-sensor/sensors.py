import abc
import time
import math
import random
import asyncio
import logging
from datetime import datetime

from logfmter import Logfmter

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
        data_rate: int = 30,
    ) -> None:

        # handle arguments
        self.sn = sn
        self.data_rate = data_rate

        self.extra = {
            'mock_type':  self.__class__.__name__,
            'sn': self.sn,
            'data_rate': self.data_rate,
        }

        # run flag
        self.doRun = False

        # Buffer of events to send
        self.data_buffer = None
        self.task_list = []

    def set_data_buffer(self, buffer):
        self.data_buffer = buffer

    def start(self):
        asyncio.get_running_loop().create_task(self.run())

    async def run(self):
        self.doRun = True

        # start loops
        self.task_list.append(asyncio.get_running_loop().create_task(self.data_loop()))

        while self.doRun:
            await asyncio.sleep(1)

        # this only shuts down the data_loop to allow last message(s) to go through
        for task in self.task_list:
            task.cancel()

        L.info("Shutting down", extra=self.extra)

    # derived classes define how data is created
    @abc.abstractmethod
    async def data_loop(self):
        pass

    def shutdown(self):
        self.doRun = False


class TestSensor1D(MockSensor):

    metadata = {
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
            }
        }
    }

    async def data_loop(self):

        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        L.info("Starting data_loop", extra=self.extra)
        await asyncio.sleep(time_to_next(self.data_rate))
        while True:
            variables = dict()

            dt = datetime.utcnow()
            dt_str = datetime.strftime(dt, MockSensor.isofmt)

            variables["time"] = dt_str
            variables["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
            variables["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
            variables["altitude"] = round(100 + random.uniform(-10, 10), 3)

            variables["temperature"] = round(25 + random.uniform(-3, 3), 3)
            variables["rh"] = round(60 + random.uniform(-5, 5), 3)
            variables["wind_speed"] = round(10 + random.uniform(-5, 5), 3)
            variables["wind_direction"] = round(90 + random.uniform(-20, 20), 3)

            data = {
                "data": variables,
                "instance": {
                    "make": "MockCo",
                    "model": "Sensor-1",
                    "serial": self.sn
                }
            }
            # If we send a message on an even 10-minute mark then
            # include the metadata packet. This is meant to mock
            # occasionally updating a station-sensors's metadata
            if dt.minute % 10 == 0:
                data["metadata"] = self.metadata
                data["metadata"]["attributes"] = data["instance"]

            if self.data_buffer:
                await self.data_buffer.put(data)

            await asyncio.sleep(time_to_next(self.data_rate))


class TestSensor2D(MockSensor):

    metadata = {
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
            }
        }
    }

    async def data_loop(self):

        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        L.info("Starting data_loop", extra=self.extra)
        await asyncio.sleep(time_to_next(self.data_rate))
        while True:
            variables = dict()

            dt = datetime.utcnow()
            dt_str = datetime.strftime(dt, MockSensor.isofmt)

            variables["time"] = dt_str
            variables["diameter"] = [0.1, 0.2, 0.35, 0.5, 0.75, 1.0]
            # variables["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
            # variables["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
            # variables["altitude"] = round(100 + random.uniform(-10, 10), 3)
            variables["temperature"] = round(25 + random.uniform(-3, 3), 3)
            variables["rh"] = round(60 + random.uniform(-5, 5), 3)

            base_count = [10, 15, 25, 20, 12, 5]
            count = []
            for bc in base_count:
                count.append(int(bc + random.uniform(-2, 2)))
            variables["bin_counts"] = count

            data = {
                "data": variables,
                "instance": {
                    "make": "MockCo",
                    "model": "Sensor-2",
                    "serial": self.sn
                }
            }
            # If we send a message on an even 10-minute mark then
            # include the metadata packet. This is meant to mock
            # occasionally updating a station-sensors's metadata
            if dt.minute % 10 == 0:
                data["metadata"] = self.metadata
                data["metadata"]["attributes"] = data["instance"]

            if self.data_buffer:
                await self.data_buffer.put(data)

            await asyncio.sleep(time_to_next(self.data_rate))
