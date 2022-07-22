import abc
import logging
import asyncio

from logfmter import Logfmter
from cloudevents.http import CloudEvent, to_structured

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger('mock_sensor')
L.setLevel(logging.INFO)


class DataSource(abc.ABC):

    def __init__(self, name, mqtt_client, mqtt_topic_prefix, dry_run) -> None:
        super().__init__()

        self.name = name

        self.dry_run = dry_run
        self.mqtt_client = mqtt_client
        self.mqtt_topic_prefix = mqtt_topic_prefix

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

    async def send_loop(self):

        topic = "/".join(
            [
                x for x in [
                    self.mqtt_topic_prefix,
                    self.metadata["attributes"]["source-type"],
                    "data"
                ]
                if x
            ]
        )

        while True:
            event = await self.send_buffer.get()
            _, body = to_structured(event)

            meta = {
                'topic': topic,
                'source': event._attributes['source'],
                **event.data['data']
            }

            if not self.dry_run:
                await self.mqtt_client.publish(
                    topic, body, qos=0
                )
                L.info(f"Published", extra=meta)
            else:
                L.info(f"[DRY_RUN]", extra=meta)
            await asyncio.sleep(0.1)

    def start(self):
        asyncio.get_running_loop().create_task(self.run())
        for sensor in self.sensor_list:
            sensor.start()

    async def run(self):
        self.doRun = True

        # start loops
        asyncio.get_running_loop().create_task(self.ce_loop())

        while self.doRun:
            await asyncio.sleep(1)

        for sensor in self.sensor_list:
            sensor.shutdown()

    def shutdown(self):
        for sensor in self.sensor_list:
            sensor.shutdown()

        self.doRun = False


class ACGDAQ(DataSource):

    metadata = {
        "attributes": {
            "source-type": "acg-daq",
            "content-type": "application/cloudevents+json; charset=utf-8",
        }
    }

    async def ce_loop(self):

        # get data from queue, package into cloudevent, send via mqtt
        while True:
            data = await self.data_buffer.get()
            try:
                sensor_atts = data["instance"]
                sensor_make = sensor_atts["make"]
                sensor_model = sensor_atts["model"]
                sn = sensor_atts["serial"]
                attributes = {
                    "type": f"gov.noaa.pmel.acg.data.insert.envds.v2",
                    "source": f"/sensor/{sensor_make}/{sensor_model}/{sn}",
                    "datacontenttype": "application/json; charset=utf-8",
                }

                payload = {
                    "metadata": data.get('metadata', {}),
                    "data": data.get('data', {})
                }
                ce = CloudEvent(attributes=attributes, data=payload)
                await self.send_buffer.put(ce)
            except KeyError:
                pass

            await asyncio.sleep(0.1)
