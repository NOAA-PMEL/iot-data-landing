import signal
import asyncio
import logging

from logfmter import Logfmter
import paho.mqtt.client as mqtt
from pydantic import BaseSettings
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

from sensors import TestSensor1D, TestSensor2D

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger('mock_sensor')
L.setLevel(logging.INFO)


class Settings(BaseSettings):
    mqtt_broker: str = 'localhost'
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = 'instrument/data'
    dry_run: bool = True

    class Config:
        env_prefix = 'IOT_MOCK_SENSOR_'
        case_sensitive = False


config = Settings()


async def main_run(sensors):

    # start all sensors
    for sensor in sensors:
        sensor.start()

    await asyncio.sleep(1.0)
    while any([sensor.doRun for sensor in sensors]):

        await asyncio.sleep(1)

    # wait for tasks to complete
    L.info("shutting down - wait for tasks to finish")
    await asyncio.sleep(2.0)


async def main():
    event_loop = asyncio.get_running_loop()

    # create mqtt client
    mqtt_client = mqtt.Client("dataserver", protocol=mqtt.MQTTv5)

    # mqtt_client.tls_set(ca_certs='./mqtt/certs/ca.crt', cert_reqs=ssl.CERT_NONE)
    # mqtt_client.tls_insecure_set(True)
    mqtt_client.on_message = on_message
    mqtt_client.on_publish = on_publish

    properties = Properties(PacketTypes.PUBLISH)
    properties.ContentType = "application/cloudevents+json; charset=utf-8"

    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # mqtt_client.tls_set_context(context)

    mqtt_client.connect(
        host=config.mqtt_broker,
        port=config.mqtt_port
    )

    prefix = config.mqtt_topic_prefix

    sensors = []
    # 1D
    sensors.append(TestSensor1D(sn="1234", mqtt_client=mqtt_client, mqtt_topic_prefix=prefix))
    sensors.append(TestSensor1D(sn="2345", mqtt_client=mqtt_client, mqtt_topic_prefix=prefix))
    sensors.append(TestSensor1D(sn="3456", mqtt_client=mqtt_client, mqtt_topic_prefix=prefix, data_rate=5))
    # 2D
    sensors.append(TestSensor2D(sn="3234", mqtt_client=mqtt_client, mqtt_topic_prefix=prefix))
    sensors.append(TestSensor2D(sn="3345", mqtt_client=mqtt_client, mqtt_topic_prefix=prefix))
    sensors.append(TestSensor2D(sn="3456", mqtt_client=mqtt_client, mqtt_topic_prefix=prefix, data_rate=5))

    def shutdown_handler(*args):
        for sensor in sensors:
            sensor.shutdown()

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    L.debug("main: Started")
    await main_run(sensors)


def on_message(client, userdata, message):
    print("message received ", str(message.payload.decode("utf-8")))
    print("message topic=", message.topic)
    print("message qos=", message.qos)
    print("message retain flag=", message.retain)


def on_publish(client, userdata, mid):
    L.debug("mqtt data published: %s, result: %s", userdata, mid)


if __name__ == "__main__":
    asyncio.run(main())
