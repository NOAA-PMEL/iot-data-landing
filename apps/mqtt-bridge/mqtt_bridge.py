import uuid
import logging
import asyncio

import httpx
from logfmter import Logfmter
from pydantic import BaseSettings, Field
from asyncio_mqtt import Client, MqttError
from cloudevents.http import to_structured, from_json
from cloudevents.exceptions import InvalidStructuredJSON

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)


class Settings(BaseSettings):
    mqtt_broker: str = 'localhost'
    mqtt_port: int = 1883
    mqtt_topic_filter: str = 'instrument/data/+'
    mqtt_topic_subscription: str = 'instrument/#'
    mqtt_client_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    knative_broker: str = 'http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default'
    dry_run: bool = False

    class Config:
        env_prefix = 'MQTT_BRIDGE_'
        case_sensitive = False


config = Settings()


async def listen():
    async with Client(config.mqtt_broker, port=config.mqtt_port) as client:
        async with client.filtered_messages(config.mqtt_topic_filter) as messages:
            await client.subscribe(config.mqtt_topic_subscription)

            L.info(
                "Subscribed",
                extra={ k: v for k, v in config.dict().items() if k.lower().startswith('mqtt_') }
            )

            template = {
                'topic_filter': config.mqtt_topic_filter,
                'subscription': config.mqtt_topic_subscription
            }
            await publish_messages(messages, template)


async def publish_messages(messages, template):
    async for message in messages:
        try:
            payload = message.payload.decode()
            data = from_json(payload)
        except InvalidStructuredJSON:
            L.error(f"INVALID MSG: {payload}", extra=template)

        # Always log the message
        L.info(data, extra=template)
        # Send the messages on to Kafka if we aren't in a dry_run
        if config.dry_run is False:
            try:
                headers, body = to_structured(data)
                # send to knative kafkabroker
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        config.knative_broker,
                        headers=headers,
                        data=body.decode()
                    )
                    r.raise_for_status()
            except InvalidStructuredJSON:
                L.error(f"INVALID MSG: {payload}")
            except httpx.HTTPError as e:
                L.error(f"HTTP Error when posting to {e.request.url!r}: {e}")


async def main():
    L.info("Starting", extra=config.dict())
    reconnect = 3
    while True:
        try:
            await listen()
        except MqttError as error:
            L.error(
                f'{error}. Trying again in {reconnect} seconds',
                extra={ k: v for k, v in config.dict().items() if k.lower().startswith('mqtt_') }
            )
        finally:
            await asyncio.sleep(reconnect)


if __name__ == '__main__':
    asyncio.run(main())
