# from pykafka import KafkaClient

# client = KafkaClient(hosts="161.55.39.7:9094")
# topic = client.topics["instrument-data"]
# consumer = topic.get_simple_consumer()
# # print(consumer.held_offsets)
# # for message in consumer:
# #     if message is not None:
# #         print(f"offset={message.offset}, value={message.value}")
# with topic.get_sync_producer() as producer:
#     for i in range(4):
#         # print(f'{"test message": {(i ** 2)}}')
#         # producer.produce(f'{"test message":  {(i ** 2)}}')
#         producer.produce((f"test message {(i ** 2)}").encode('ascii'))


import asyncio
import signal
import requests
from cloudevents.http import to_structured, from_json
from cloudevents.exceptions import InvalidStructuredJSON
import uuid

from gmqtt import Client as MQTTClient

# gmqtt also compatibility with uvloop  
# import uvloop
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# STOP = asyncio.Event()

do_run = True

def on_connect(client, flags, rc, properties):
    print('Connected')
    client.subscribe('instrument/data', qos=0)


def on_message(client, topic, payload, qos, properties):
    print('RECV MSG:', payload)

    # when class based, will send to a queue for handling but for now...
    # verify it's a cloudevent
    try:
        data = from_json(payload)

        # send to knative kafkabroker
        headers, body = to_structured(data)
        print(f"headers: {headers}")
        print(f"body: {body}")
        # url = "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/test1/test1 "
        url = "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default"
        # url = "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/iot/default"
        # url = "http://localhost:5000"
        # url = "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/iot/iot-broker"
        requests.post(url, headers=headers, data=body)
        # print(f"request.post: {url}, {headers}, {data}")

    except InvalidStructuredJSON:
        # self.logger.warn("invalid message type %s")
        pass


def on_disconnect(client, packet, exc=None):
    print('Disconnected')

def on_subscribe(client, mid, qos, properties):
    print('SUBSCRIBED')

def ask_exit(*args):
    print("ask_exit")
    # STOP.set()
    global do_run
    do_run = False

# async def main(broker_host, token):
async def main():
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)

    config = {
        "client_id": "iot-bridge",
        "host": "roosevelt.pmel.noaa.gov",
        "port": 1883,
        "keepalive": 60,
        "clean_session": False,  # need to look at what this means
        "qos_level_pub": 0,
        "qos_level_sub": 0,
        "subscriptions": [],
        "ssl_context": None,
    }

    # client = MQTTClient("iot-bridge2")
    id = f"{uuid.uuid4()}"
    print(id)
    client = MQTTClient(id)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe

    # client.set_auth_credentials(token, None)
    await client.connect("roosevelt.pmel.noaa.gov", keepalive=60)

    # client.publish('TEST/TIME', str(time.time()), qos=1)

    # await STOP.wait()
    global do_run
    while do_run:
        await asyncio.sleep(1)

    await client.disconnect()


if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop = asyncio.get_running_loop()

    # host = 'roosevelt.pmel.noaa.gov'
    host = 'roosevelt.pmel.noaa.gov'
    # token = os.environ.get('FLESPI_TOKEN')

    # loop.add_signal_handler(signal.SIGINT, ask_exit)
    # loop.add_signal_handler(signal.SIGTERM, ask_exit)
    
    asyncio.run(main())
    # loop.run_until_complete(main(host, token))