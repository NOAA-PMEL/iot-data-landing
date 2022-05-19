import abc
from datetime import datetime
import math

# import os
import signal
import sys
import asyncio

# import json
import random

# from cloudevents.http import CloudEvent, event, from_json, to_structured
from cloudevents.http import CloudEvent, to_structured
from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

try:
    from client import MQTTClient
except ModuleNotFoundError:
    pass
# from mock_sensor.client import MQTTClient

import logging
import time


class DataSource(abc.ABC):

    def __init__(self, name, mqtt_client) -> None:
        super().__init__()

        self.name = name
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("starting data source")

        self.mqtt_client = mqtt_client
        self.sensor_list = []

        self.data_buffer = asyncio.Queue()
        self.send_buffer = asyncio.Queue()

        asyncio.get_running_loop().create_task(self.send_loop())


    def add_sensors(self, sensor_list):
        if sensor_list:
            for sensor in sensor_list:
                self.add_sensor(sensor)

    def add_sensor(self, sensor):
        if sensor:
            sensor.set_data_buffer(self.data_buffer)
            self.sensor_list.append(sensor)

    def get_source_id(self):
        return "-".join([self.metadata["attributes"]["source-type"], self.name])

    async def send_loop(self):

        # properties = Properties(PacketTypes.PUBLISH)
        # properties.ContentType = "application/cloudevents+json; charset=utf-8"
        # topic = "/".join(["aws-id", self.get_source_id(), "data"])
        topic = "/".join(["aws-id", self.metadata["attributes"]["source-type"], "data"])
        content_type = self.metadata["attributes"]["content-type"]
        # self.logger.debug("topic: %s", self.get_source_id())

        while True:
            event = await self.send_buffer.get()
            headers, body = to_structured(event)
            # print(headers, body)
            await self.mqtt_client.publish(
                topic, payload=body, qos=0, content_type=content_type
            )
            await asyncio.sleep(0.1)

    def start(self):
        asyncio.get_running_loop().create_task(self.run())
        for sensor in self.sensor_list:
            sensor.start()

    async def run(self):
        self.doRun = True

        self.logger.info("start run")

        # start loops
        # self.task_list.append(asyncio.get_running_loop().create_task(self.data_loop()))
        asyncio.get_running_loop().create_task(self.ce_loop())
        # asyncio.get_running_loop().create_task(self.send_loop())

        while self.doRun:
            pass
            await asyncio.sleep(1)

        # this only shuts down the data_loop to allow last message(s) to go through
        # for task in self.task_list:
        #     task.cancel()
        print("shutdown")

        for sensor in self.sensor_list:
            sensor.shutdown()

    def shutdown(self):
        self.logger.info("Shutting down...")

        for sensor in self.sensor_list:
            sensor.shutdown()

        self.doRun = False


class ACGDAQ(DataSource):
    def __init__(self, name, mqtt_client) -> None:
        super().__init__(name, mqtt_client)

        self.metadata = {
            "attributes": {
                "source-type": "acg-daq",
                "content-type": "application/cloudevents+json; charset=utf-8",
            },
        }

    async def ce_loop(self):

        # define type and source here
        # sensor_make = self.get_metadata()["attributes"]["make"]
        # sensor_model = self.get_metadata()["attributes"]["model"]
        # attributes = {
        #     "type": f"gov.noaa.pmel.acg.data.insert.envds.v2",
        #     "source": f"/sensor/{sensor_make}/{sensor_model}/{self.sn}",
        #     "datacontenttype": "application/json; charset=utf-8",
        # }

        # get data from queue, package into cloudevent, send via mqtt
        while True:
            data = await self.data_buffer.get()
            try:
                sensor_atts = data["attributes"]
                sensor_make = sensor_atts["make"]
                sensor_model = sensor_atts["model"]
                sn = data["instance"]["sn"]
                attributes = {
                    "type": f"gov.noaa.pmel.acg.data.insert.envds.v2",
                    "source": f"/sensor/{sensor_make}/{sensor_model}/{sn}",
                    "datacontenttype": "application/json; charset=utf-8",
                }

                payload = {"data": data["variables"]}
                ce = CloudEvent(attributes=attributes, data=payload)
                self.logger.debug("ce_loop: cloudevent = %s", ce)
                await self.send_buffer.put(ce)

            except KeyError:
                pass
            # payload = {"data": data, "metadata": self.get_metadata()}

            await asyncio.sleep(0.1)


class MockSensor(abc.ABC):

    isofmt = "%Y-%m-%dT%H:%M:%SZ"

    # derived classes must define the sensor metadata - see TestSensor1D and TestSensor2D below
    # metadata = {}

    def __init__(
        self,
        sn: str,
        # mqtt_client,
        data_rate: int = 1,
    ) -> None:

        # attach logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Starting %s", self.__class__.__name__)

        # handle arguments
        self.sn = sn
        # self.mqtt_client = mqtt_client
        self.data_rate = data_rate
        # self.mqtt_host = mqtt_host
        # self.mqtt_port = mqtt_port
        # self.mqtt_tls_cert = mqtt_tls_cert

        # define data queues
        self.data_buffer = None
        # self.data_buffer = asyncio.Queue()
        # self.payload_buffer = asyncio.Queue()
        # self.send_buffer = asyncio.Queue()
        # self.send_buffer = None

        # run flag
        self.doRun = False

        self.task_list = []

    def set_data_buffer(self, buffer):
        self.data_buffer = buffer


    @abc.abstractmethod
    def get_metadata(self):
        pass

    def start(self):
        asyncio.get_running_loop().create_task(self.run())

    async def run(self):
        self.doRun = True

        self.logger.info("start run")

        # start loops
        self.task_list.append(asyncio.get_running_loop().create_task(self.data_loop()))
        # asyncio.get_running_loop().create_task(self.ce_loop())
        # asyncio.get_running_loop().create_task(self.send_loop())

        while self.doRun:
            pass
            await asyncio.sleep(1)

        # this only shuts down the data_loop to allow last message(s) to go through
        for task in self.task_list:
            task.cancel()
        print("shutdown")

    # derived classes define how data is created
    @abc.abstractmethod
    async def data_loop(self):
        pass

    # package data into cloudevent
    # async def ce_loop(self):

    #     # define type and source here
    #     sensor_make = self.get_metadata()["attributes"]["make"]
    #     sensor_model = self.get_metadata()["attributes"]["model"]
    #     attributes = {
    #         "type": f"gov.noaa.pmel.acg.data.insert.envds.v2",
    #         "source": f"/sensor/{sensor_make}/{sensor_model}/{self.sn}",
    #         "datacontenttype": "application/json; charset=utf-8",
    #     }

    #     # get data from queue, package into cloudevent, send via mqtt
    #     while True:
    #         data = await self.data_buffer.get()
    #         # payload = {"data": data, "metadata": self.get_metadata()}
    #         payload = {"data": data}
    #         ce = CloudEvent(attributes=attributes, data=payload)
    #         self.logger.debug("ce_loop: cloudevent = %s", ce)
    #         await self.send_buffer.put(ce)

    #         await asyncio.sleep(0.1)

    # outpu to mqtt broker using paho client
    # async def send_loop(self):

    #     properties = Properties(PacketTypes.PUBLISH)
    #     properties.ContentType = "application/cloudevents+json; charset=utf-8"

    #     while True:
    #         event = await self.send_buffer.get()
    #         headers, body = to_structured(event)
    #         # print(headers, body)
    #         ret = self.mqtt_client.publish(
    #             "instrument/data", payload=body, qos=0, properties=properties
    #         )
    #         await asyncio.sleep(0.1)

    def shutdown(self):
        self.logger.info("Shutting down...")
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

    def __init__(
        self,
        sn: str,
        # mqtt_client,
        data_rate: int = 1,
        mqtt_host: str = "localhost",
        mqtt_port: int = 1883,
        mqtt_tls_cert: str = None,
    ) -> None:
        super().__init__(
            # sn, mqtt_client, data_rate, mqtt_host, mqtt_port, mqtt_tls_cert
            sn,
            data_rate,
        )

    def get_metadata(self):
        return TestSensor1D.metadata

    async def data_loop(self):

        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        self.logger.debug("Starting data_loop")
        await asyncio.sleep(time_to_next(self.data_rate))
        while True:
            variables = dict()

            dt = datetime.utcnow()
            dt_str = datetime.strftime(dt, MockSensor.isofmt)
            # print(f"dt(hour:min): {dt.hour}:{dt.minute}")
            variables["time"] = dt_str
            variables["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
            variables["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
            variables["altitude"] = round(100 + random.uniform(-10, 10), 3)

            variables["temperature"] = round(25 + random.uniform(-3, 3), 3)
            variables["rh"] = round(60 + random.uniform(-5, 5), 3)
            variables["wind_speed"] = round(10 + random.uniform(-5, 5), 3)
            variables["wind_direction"] = round(90 + random.uniform(-20, 20), 3)

            data = {
                "attributes": TestSensor1D.metadata["attributes"],
                "instance": {"sn": self.sn},
                "variables": variables,
            }
            if self.data_buffer:
                await self.data_buffer.put(data)
            await asyncio.sleep(time_to_next(self.data_rate))


class TestSensor2D(MockSensor):

    metadata = {
        "attributes": {"make": "MockCo", "model": "Sensor-2",},
        "variables": {
            "time": {"shape": ["time"], "attributes": {"long_name": "Time"},},
            "diameter": {
                "type": "double",
                "shape": ["bins"],
                "attributes": {"long_name": "Diameter", "units": "micron"},
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
                "attributes": {"long_name": "Bin Counts", "units": "count",},
            },
        },
    }

    def __init__(
        self,
        sn: str,
        # mqtt_client,
        data_rate: int = 1,
    ) -> None:
        super().__init__(
            # sn, mqtt_client, data_rate, mqtt_host, mqtt_port, mqtt_tls_cert
            sn,
            data_rate,
        )

    def get_metadata(self):
        return TestSensor2D.metadata

    async def data_loop(self):

        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        self.logger.debug("Starting data_loop")
        await asyncio.sleep(time_to_next(self.data_rate))
        while True:
            variables = dict()

            dt = datetime.utcnow()
            dt_str = datetime.strftime(dt, MockSensor.isofmt)
            # print(f"dt(hour:min): {dt.hour}:{dt.minute}")
            variables["time"] = dt_str
            variables["diameter"] = [0.1, 0.2, 0.35, 0.5, 0.75, 1.0]
            # data["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
            # data["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
            # data["altitude"] = round(100 + random.uniform(-10, 10), 3)

            variables["temperature"] = round(25 + random.uniform(-3, 3), 3)
            variables["rh"] = round(60 + random.uniform(-5, 5), 3)

            base_count = [10, 15, 25, 20, 12, 5]
            count = []
            for bc in base_count:
                count.append(int(bc + random.uniform(-2, 2)))
            variables["bin_counts"] = count

            data = {
                "attributes": TestSensor2D.metadata["attributes"],
                "instance": {"sn": self.sn},
                 "variables": variables,
            }
            if self.data_buffer:
                await self.data_buffer.put(data)
            print(f"2d data_rate: {self.data_rate}")
            await asyncio.sleep(time_to_next(self.data_rate))


def time_to_next(sec):
    now = time.time()
    delta = sec - (math.fmod(now, sec))
    return delta


async def main_run(daqs):

    # start all sensors
    for daq in daqs:
        daq.start()

    await asyncio.sleep(1.0)
    while any([daq.doRun for daq in daqs]):

        await asyncio.sleep(1)

    # wait for tasks to complete
    logging.getLogger().info("shutting down - wait for tasks to finish")
    await asyncio.sleep(2.0)


async def main():
    event_loop = asyncio.get_running_loop()
    logger = logging.getLogger()

    # mqtt_config = {"host": "localhost", "port": 1883}
    mqtt_config = {"host": "roosevelt", "port": 1883}
    mqtt_client = MQTTClient(config=mqtt_config)

    # mqtt_host = "localhost"
    # # mqtt_host = "roosevelt"
    # # mqtt_host = "wallingford"
    # mqtt_port = 1883
    # # create mqtt client
    # mqtt_client = mqtt.Client("dataserver", protocol=mqtt.MQTTv5)
    # # mqtt_client.tls_set(ca_certs='./mqtt/certs/ca.crt', cert_reqs=ssl.CERT_NONE)
    # # mqtt_client.tls_insecure_set(True)
    # mqtt_client.on_message = on_message
    # mqtt_client.on_publish = on_publish

    # properties = Properties(PacketTypes.PUBLISH)
    # properties.ContentType = "application/cloudevents+json; charset=utf-8"

    # # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # # mqtt_client.tls_set_context(context)

    # mqtt_client.connect(host=mqtt_host, port=mqtt_port)

    daqs = []
    sensors = []
    
    acgdaq = ACGDAQ(name="mock1", mqtt_client=mqtt_client)
    # 1D
    sensors.append(TestSensor1D(sn="1234"))#, mqtt_client=mqtt_client))
    sensors.append(TestSensor1D(sn="2345"))#, mqtt_client=mqtt_client))
    sensors.append(TestSensor1D(sn="3456"))#, mqtt_client=mqtt_client))
    sensors.append(TestSensor1D(sn="4567"))#, mqtt_client=mqtt_client))
    sensors.append(TestSensor1D(sn="5678"))#, mqtt_client=mqtt_client))
    sensors.append(TestSensor1D(sn="6789"))#, mqtt_client=mqtt_client))
    #2D
    sensors.append(TestSensor2D(sn="3234", data_rate=5))#, mqtt_client=mqtt_client, data_rate=5))
    sensors.append(TestSensor2D(sn="3345", data_rate=10))#, mqtt_client=mqtt_client, data_rate=10))
    sensors.append(TestSensor2D(sn="3456", data_rate=30))#, mqtt_client=mqtt_client, data_rate=30))

    acgdaq.add_sensors(sensors)
    daqs.append(acgdaq)


    def shutdown_handler(*args):
        # for sensor in sensors:
        #     sensor.shutdown()
        for daq in daqs:
            daq.shutdown()

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    logger.debug("main: Started")
    await main_run(daqs)


def on_message(client, userdata, message):
    print("message received ", str(message.payload.decode("utf-8")))
    print("message topic=", message.topic)
    print("message qos=", message.qos)
    print("message retain flag=", message.retain)


def on_publish(client, userdata, mid):
    logging.getLogger().debug("mqtt data published: %s, result: %s", userdata, mid)
    # print(f"data pubished: {userdata}, result: {mid}")


if __name__ == "__main__":
    try:
        from mock_sensor.mock import MQTTClient
    except ModuleNotFoundError:
        pass

    # set up logging - send to stdout
    log_level = logging.DEBUG
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        # datefmt=MockSensor.isofmt,
    )
    handler.setFormatter(formatter)

    # handler = logging.StreamHandler(sys.stdout)
    root_logger.addHandler(handler)

    # get params from file

    asyncio.run(main())
