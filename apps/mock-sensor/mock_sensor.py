import signal
import asyncio
import logging

from logfmter import Logfmter
from asyncio_mqtt import Client
from pydantic import BaseSettings

from sources import ACGDAQ
from sensors import TestSensor1D, TestSensor2D

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger('mock_sensor')
L.setLevel(logging.INFO)


class Settings(BaseSettings):
    mqtt_broker: str = 'localhost'
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = 'aws-id'
    dry_run: bool = False

    class Config:
        env_prefix = 'IOT_MOCK_SENSOR_'
        case_sensitive = False


config = Settings()


async def main_run(daqs):

    # start all sensors
    for daq in daqs:
        daq.start()

    await asyncio.sleep(1.0)
    while any([daq.doRun for daq in daqs]):
        await asyncio.sleep(1)

    # wait for tasks to complete
    L.info("shutting down - wait for tasks to finish")
    await asyncio.sleep(2.0)


async def main():

    async with Client(config.mqtt_broker, port=config.mqtt_port) as mqtt_client:
        sensors = []
        # 1D
        sensors.append(TestSensor1D(sn="1234"))
        sensors.append(TestSensor1D(sn="2345"))
        sensors.append(TestSensor1D(sn="3456", data_rate=5))
        # 2D
        sensors.append(TestSensor2D(sn="4567"))
        sensors.append(TestSensor2D(sn="5678"))
        sensors.append(TestSensor2D(sn="6789", data_rate=5))

        event_loop = asyncio.get_running_loop()

        acgdaq = ACGDAQ(
            name="mock1",
            mqtt_client=mqtt_client,
            mqtt_topic_prefix=config.mqtt_topic_prefix,
            dry_run=config.dry_run
        )
        acgdaq.add_sensors(sensors)

        daqs = [
            acgdaq
        ]

        def shutdown_handler(*args):
            for daq in daqs:
                daq.shutdown()

        event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
        event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

        L.debug("main: Started")
        await main_run(daqs)


if __name__ == "__main__":
    asyncio.run(main())
