import abc
from datetime import datetime
import math
import os
import signal
import sys
import asyncio
import json
import random

from cloudevents.http import CloudEvent, event, from_json, to_structured
from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

import logging
import time


class MockSensor(abc.ABC):

    isofmt = "%Y-%m-%dT%H:%M:%SZ"

    # derived classes must define the sensor data
    # metadata = {
    #     "make": "MockCo",
    #     "model": "Sensor_1",
    #     "variables": {
    #         "time": {"long_name": "Time"},
    #         "latitude": {
    #             "long_name": "Latitude",
    #             "data_type": "double",
    #             "units": "degrees_north",
    #         },
    #         "longitude": {
    #             "long_name": "Longitude",
    #             "data_type": "double",
    #             "units": "degrees_east",
    #         },
    #         "altitude": {"long_name": "Altitude", "data_type": "double", "units": "m"},
    #         "temperature": {
    #             "long_name": "Temperature",
    #             "data_type": "double",
    #             "units": "degree_C",
    #         },
    #         "rh": {"long_name": "RH", "data_type": "double", "units": "percent"},
    #         "wind_speed": {
    #             "long_name": "Wind Speed",
    #             "data_type": "double",
    #             "units": "m s-1",
    #         },
    #         "wind_direction": {
    #             "long_name": "Wind Direction",
    #             "data_type": "double",
    #             "units": "degree",
    #         },
    #     },
    # }

    def __init__(
        self,
        sn: str,
        mqtt_client,
        data_rate: int = 1,
        mqtt_host: str = "localhost",
        mqtt_port: int = 1883,
        mqtt_tls_cert: str = None,
    ) -> None:

        # attach logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Starting %s", self.__class__.__name__)

        # handle arguments
        self.sn = sn
        self.mqtt_client = mqtt_client
        self.data_rate = data_rate
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

    async def run(self):
        self.doRun = True

        self.logger.info("start run")

        # start loops
        self.task_list.append(asyncio.get_running_loop().create_task(self.data_loop()))
        self.task_list.append(asyncio.get_running_loop().create_task(self.ce_loop()))
        self.task_list.append(asyncio.get_running_loop().create_task(self.send_loop()))

        while self.doRun:
            pass
            await asyncio.sleep(1)

        print("shutdown")

    async def data_loop(self):

        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        self.logger.debug("Starting data_loop")
        await asyncio.sleep(time_to_next(self.data_rate))
        while True:
            data = dict()

            dt = datetime.utcnow()
            dt_str = datetime.strftime(dt, MockSensor.isofmt)
            # print(f"dt(hour:min): {dt.hour}:{dt.minute}")
            data["time"] = dt_str
            data["latitude"] = round(10 + random.uniform(-1,1)/10, 3)
            data["longitude"] = round(-150 + random.uniform(-1,1)/10, 3)
            data["altitude"] = round(100 + random.uniform(-10,10), 3)

            data["temperature"] = round(25 + random.uniform(-3,3), 3)
            data["rh"] = round(60 + random.uniform(-5,5), 3)
            data["wind_speed"] = round(10 + random.uniform(-5,5), 3)
            data["wind_dir"] = round(90 + random.uniform(-20,20), 3)

            await self.data_buffer.put(data)
            await asyncio.sleep(time_to_next(self.data_rate))

    # package data into cloudevent
    async def ce_loop(self):
        
        # define type and source here
        attributes = {
            "type": f"gov.noaa.pmel.acg.data.insert.envds.v2",
            "source": f"/sensor/{self.get_metadata()['make']}/{self.get_metadata()['model']}/{self.sn}",
            "datacontenttype" : "application/json; charset=utf-8",
        }

        # get data from queue, package into cloudevent, send via mqtt
        while True:
            data = await self.data_buffer.get()
            # payload = {"data": data, "metadata": self.get_metadata()}
            payload = {"data": data}
            ce = CloudEvent(attributes=attributes, data=payload)
            self.logger.debug("ce_loop: cloudevent = %s", ce)
            await self.send_buffer.put(ce)

            await asyncio.sleep(.1)

    # outpu to mqtt broker using paho client
    async def send_loop(self):
        
        properties = Properties(PacketTypes.PUBLISH)
        properties.ContentType = 'application/cloudevents+json; charset=utf-8'
        
        while True:
            event = await self.send_buffer.get()
            headers, body = to_structured(event)
            ret = self.mqtt_client.publish("instrument/data", payload=body, qos=0, properties=properties)
            await asyncio.sleep(.1)

    def shutdown(self):
        self.logger.info("Shutting down...")
        self.doRun = False

class TestSensor1D(MockSensor):

    metadata = {
        "make": "MockCo",
        "model": "Sensor_1",
        "variables": {
            "time": {"long_name": "Time", "dimension": ["time"]},
            "latitude": {
                "long_name": "Latitude",
                "data_type": "double",
                "units": "degrees_north",
                "dimension": ["time"]
            },
            "longitude": {
                "long_name": "Longitude",
                "data_type": "double",
                "units": "degrees_east",
                "dimension": ["time"]
            },
            "altitude": {"long_name": "Altitude", "data_type": "double", "units": "m"},
            "temperature": {
                "long_name": "Temperature",
                "data_type": "double",
                "units": "degree_C",
                "dimension": ["time"]
            },
            "rh": {"long_name": "RH", "data_type": "double", "units": "percent"},
            "wind_speed": {
                "long_name": "Wind Speed",
                "data_type": "double",
                "units": "m s-1",
                "dimension": ["time"]
            },
            "wind_direction": {
                "long_name": "Wind Direction",
                "data_type": "double",
                "units": "degree",
                "dimension": ["time"]
            },
        },
    }

    def __init__(self, sn: str, mqtt_client, data_rate: int = 1, mqtt_host: str = "localhost", mqtt_port: int = 1883, mqtt_tls_cert: str = None) -> None:
        super().__init__(sn, mqtt_client, data_rate, mqtt_host, mqtt_port, mqtt_tls_cert)

    def get_metadata(self):
        return TestSensor1D.metadata


def time_to_next(sec):
    now = time.time()
    delta = sec - (math.fmod(now, sec))
    return delta


async def main():
    event_loop = asyncio.get_running_loop()
    logger = logging.getLogger()

    mqtt_host = "localhost"
    mqtt_port = 1883
    # create mqtt client
    mqtt_client = mqtt.Client("dataserver",protocol=mqtt.MQTTv5)
    # mqtt_client.tls_set(ca_certs='./mqtt/certs/ca.crt', cert_reqs=ssl.CERT_NONE)
    # mqtt_client.tls_insecure_set(True)
    mqtt_client.on_message = on_message
    mqtt_client.on_publish = on_publish

    properties = Properties(PacketTypes.PUBLISH)
    properties.ContentType = 'application/cloudevents+json; charset=utf-8'

    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # mqtt_client.tls_set_context(context)

    mqtt_client.connect(host=mqtt_host, port=mqtt_port)


    mock = TestSensor1D(sn="1234", mqtt_client=mqtt_client)

    event_loop.add_signal_handler(signal.SIGINT, mock.shutdown)
    event_loop.add_signal_handler(signal.SIGTERM, mock.shutdown)

    logger.debug("main: Started")
    await mock.run()

def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    
def on_publish(client, userdata, mid):
    logging.getLogger().debug("mqtt data published: %s, result: %s", userdata, mid)
    # print(f"data pubished: {userdata}, result: {mid}")


if __name__ == "__main__":

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
