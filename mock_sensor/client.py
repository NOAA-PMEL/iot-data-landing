import asyncio
import logging
import sys
import uuid
from gmqtt import Client as GMQTTClient

class MQTTClient():
    def __init__(self, config=None, **kwargs) -> None:
        
        self.logger = logging.getLogger(self.__class__.__name__)

        self.client = None

        # default config settings and template
        self.config = {
            "client_id": f"{uuid.uuid4()}",
            "host": "localhost",
            "port": 1883,
            "keepalive": 60,
            "clean_session": False,  # need to look at what this means
            "qos_level_pub": 0,
            "qos_level_sub": 0,
            "subscriptions": [],
            "ssl_context": None,
        }
        self.handle_config(config, **kwargs)

        self.pub_data = asyncio.Queue()
        self.sub_data = asyncio.Queue()

        self.subscriptions = []

        self.task_list = []
        self.task_list.append(asyncio.get_running_loop().create_task(self.publisher()))
        self.task_list.append(asyncio.get_running_loop().create_task(self.connect()))

        self.create()

    def handle_config(self, config=None, **kwargs):
        # super().handle_config(config=config)

        if config:
            for key, val in config.items():
                try:
                    self.config[key] = val
                except KeyError:
                    pass
    
        # kwargs override config
        for key, val in kwargs.items():
            try:
                self.config[key] = val
            except KeyError:
                pass

        # if "host" in kwargs:
        #     self.config["host"] = kwargs["host"]

        # if "port" in kwargs:
        #     self.config["port"] = kwargs["port"]

    def create(self):

        if self.config:
            client_config = {
                "client_id": self.config["client_id"],
                "clean_session": self.config["clean_session"],
                # "keepalive": self.config["keepalive"]
            }
            self.client = GMQTTClient(**client_config)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            # self.client.on_subscribe = self.on_subscribe
            # self.client.on_message = self.on_message
            self.logger.debug("client created")

    async def connect(self):

        connect_config = {
            "host": self.config["host"],
            "port": self.config["port"],
            "keepalive": self.config["keepalive"],
        }
        if self.config["ssl_context"]:
            connect_config["ssl"] = self.config["ssl_context"]

        self.logger.debug("connect config: %s", connect_config)
        # await self.client.connect(**connect_config)
        await self.client.connect(host=connect_config["host"], port=self.config["port"])
        self.logger.debug(f"connected: {self.client}")

    async def disconnect(self):
        # for topic in self.subscriptions:
        #     self.client.unsubscribe(topic)
        await self.client.disconnect()
        self.logger.debug("disconnect")

    async def subscribe_channel(self, channel: str):
        while not self.client.is_connected:
            await asyncio.sleep(1)

        topic = self.to_channel(channel)
        if topic not in self.subscriptions:
            self.subscriptions.append(topic)
        self.client.unsubscribe(topic)
        await asyncio.sleep(.1)
        self.client.subscribe(topic, qos=self.config["qos_level_sub"])
        # return super().subscribe_channel(channel)

    def on_connect(self, client, flags, rc, properties):
        self.logger.debug(
            "%s connected to %s:%s",
            self.config["client_id"],
            self.config["host"],
            self.config["port"],
        )
        self.logger.debug("client connected: client:%s", client)
        self.logger.debug("client connected: flags: %s", flags)
        self.logger.debug("client connected: rc: %s", rc)
        self.logger.debug("client connected: properties: %s", properties)

        # self.loop.create_task(self.subscribe_channel_list(self.config["subscriptions"]))

    # async def on_message(self, client, topic, payload, qos, properties):
    #     # print(f"{properties}, {payload}")
    #     # print(f"{topic}: {payload}")
    #     # ce = from_json(payload)
    #     try:
    #         message = from_json(payload)

    #         # event = EventData().from_payload(payload)
    #         data = {"channel": topic, "message": message}
    #         self.logger.debug("on_message: topic: %s, message: %s", topic, message)
    #         # qmsg = {"topic": topic, "event": event}
    #         await self.sub_data.put(data)
    #         if self.sub_data.qsize() > self.queue_size_limit:
    #             self.logger.warn(
    #                 "sub_data queue count is %s (limit=%s)",
    #                 self.sub_data.qsize(),
    #                 self.queue_size_limit,
    #             )
    #     except InvalidStructuredJSON:
    #         self.logger.warn("invalid message type %s")

    #     # await self.from_broker.put(event)
    #     # self.logger.debug(f'{topic}: {ce["type"]}: {ce["source"]}, {ce.data}')
    #     # self.logger.debug('%s: %s: %s, {ce.data}', topic, ce["type"], ce["source"])
    #     return 0

    def on_disconnect(self, client, packet, exc=None):
        self.logger.debug(
            "%s disconnected from %s:%s",
            self.config["client_id"],
            self.config["host"],
            self.config["port"],
        )
        # self.do_run = False

    # def on_subscribe(self, client, mid, qos, properties):
    #     self.logger.debug(
    #         "%s subscribed to %s",
    #         self.config["client_id"],
    #         mid,
    #         # self.config["client_id"],
    #         # self.config["host"],
    #         # self.config["port"],
    #     )
    #     # self.logger.info("%s subscribed to %s", self.msg_broker_client_id, mid)


    async def publish(self, topic, payload=None, qos=0, content_type=None, **kwargs):
        message = {
            "topic": topic,
            "payload": payload,
            "qos": qos,
            "content-type": content_type
        }
        await self.pub_data.put(message)

    async def publisher(self):

        wait = True
        while wait:
            if self.client and self.client.is_connected:
                wait = False
            await asyncio.sleep(1)

        # await asyncio.sleep(10)
        while True:
            message = await self.pub_data.get()
            try:
                topic = message["topic"]
                if topic:
                    self.client.publish(
                        topic,
                        payload=message["payload"],
                        qos=message["qos"],
                        content_type=message["content-type"],
                    )
                else:
                    self.logger.warn("attempt to publish to topic=None")
            except:
                self.logger.warn("attemp to send bad message")

            await asyncio.sleep(0.1)

async def main():
    event_loop = asyncio.get_running_loop()
    client = MQTTClient()
    # await client.connect()
    content_type = "application/cloudevents+json; charset=utf-8"
    # await asyncio.sleep(10)
    while True:

        attributes = {
            "type": f"gov.noaa.pmel.acg.data.insert.envds.v2",
            "source": f"/sensor/test/test1",
            "datacontenttype": "application/json; charset=utf-8",
        }

        payload = {"data": "test data"}
        ce = CloudEvent(attributes=attributes, data=payload)
        # self.logger.debug("ce_loop: cloudevent = %s", ce)
        headers, body = to_structured(ce)

        await client.publish("/iot/acg-main", payload=body, content_type=content_type)
        await asyncio.sleep(1)

if __name__ == "__main__": 
    # client = MQTTClient()
    from cloudevents.http import CloudEvent, to_structured
    from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields

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
