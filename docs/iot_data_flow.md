# IoT Data Flow
The following is an attmept to describe what I am thinking about how the incoming data will arrive at the MQTT gateway and then be passed in to the system.

## Data source
As we do not currently have any "true" IoT type of sensors that I know if in the lab, all instruments/sensors will have to be converted via some data acquistion or converter application. Each source of data will have to provide their own way of getting data ready for transmission via MQTT to the broker. 

Looking at the IoT solutions for AWS and GCP, they require a registration of "Things" or "sensors". In our case, I'm looking at a "thing" being the DAQ/Converter source as the registered entity. The source would publish data to the broker on a defined topic for that source (as opposed to each instrument/sensor having their own topic). The data will be transmitted as a data packet wrapped in a CloudEvent envelope where the "type" of the data corresonds to the DAQ/Converter system sending the data and the "source" would have information about the actual instrument (e.g., /make/model/sn). 

So, data coming into the lab from a particular source will contain a data record for a specific instrument but it could be any one of the instruments controlled by that data source. The logic used to route and parse the payloads will be handled by data source and istrument specific handlers that each group (or data format manager) will provide.

In theory, this will extend to cases if/when we do start using IoT capable sensors as each will register as their own "thing" (source) and be parsed by user supplied handlers on the PMEL side.

## Data ingress layer (MQTT brokers)
From a security perspective, this is the biggest issue that needs to be resolved as it is the point where data is moving from insecure networks to the secure network at PMEL. Since I don't believe there is a solution for this yet, I have a few ideas to add to the discussion.

### DMZ layer
This would have an MQTT broker at each insecure interface (e.g., public and instrument LAN). The PMEL side of this broker would be a DMZ type of network that would allow for the message to be verified. Once verified, the message could be published to an internal MQTT broker that could be read from the secure network. 
 - Public MQTT broker - most likely AWS or GCP Iot Core broker
 - Instrument LAN broker - could be AWS, GCP or something like a Mosquitto broker as the instrument LAN is less exposure than the public
 - DMZ verification - service that subscribes to incoming data, verifies and republishes to internal MQTT broker
 - Internal MQTT broker - most likely a Mosquitto (or something like it) broker

 ### Security and verification
 There are three potential areas where security can be strengthened (at least three that I know of):
  - Connection - most likely use TLS to secure the connection. Certificates would have to be shared with the clients, I believe
  - Authentication - when the MQTT client opens the connection, it should authenticate with the broker (?). This authentication could be simple username/password or some type of certificate or encryption key. For example, GCP IoT uses Java Web Tokens (JWT) that are registered at Google as the authentication method.
  - Payload encryption - this could full encryption or some type of signed checksum. I'm sure there a ton of other options but just a couple for now. 

### Multiple MQTT brokers
This idea could be useful depending on how the system is designed. It is conceivable that much of the infrastructure on the backend will be on-prem but the public broker would still be a cloud service to leverage the security the can offer. This means much of the cost of the system would be based on the number of messages (data) moving through the broker and the egress costs to bring the data to the on-prem servers. The data arriving at the public broker would be lower frequency (moorings) or field data that might only transmit a subset of the data (e.g., 1/min sent vs 1/sec sampled) due to bandwidth limitations. Once the field system returns to the lab, the entirety of the data could be transmitted but it would not be necessary to move all the data through that broker if we had a second broker avaialble to the instrument LAN. This data could be verified and routed just as the pubclic interface but using non-cloud resources. This would work even if the whole system resides in a cloud infrastructure but would not require the costs of running larger amounts of data through the cloud vendor service.

## Data processing layer
Once the data message (events) have been verified, they will be made available on the internal MQTT broker. An application/service will get data from the broker and "inject" messages into the system (what that system looks like is not yet known but will be discussed below). Once in the system, the messages will be filtered on cloudevent type to get them the proper parser/handler where they can then be parsed/handled based on the known source type. From there, the data can be send to ERDDAP and whatever other services are created to process, view, etc the data.

## Infrastructure (the "system")
Another big question for this project is determining whether this whole system should be in the cloud, on-prem or some hybrid. Furthermore, regardless of location, how much will we attempt to make this vendor agnostic? My goal would be to be as agnostic as possible but how that looks will depend on lab support. The major pieces of the infrastructure:
 - MQTT broker - as discussed above, the cloud offers an established security model for the public facing broker but it could be that a Mosquitto (or other) broker could be configured to be as secure.
 - Message bus - this could be any form of pub/sub, queue, datastore, etc. Examples would be AWS SNS or SQS, GCP pubsub, redis, and Kafka.
 - Serverless - AWS Lambda, GCP Cloud functions(?), Knative
 - Eventing/Triggers - AWS (?), GCP (?), Kafka, Knative
 - Data server - ERDDAP
 - Database - SQL or noSQL - used for metadata, registries.

How we implement those services depends on how vendor agnostic we attempt to be. Designing this as an AWS ecosystem, there are options for all of these services. But if we want to be as agnostic as possible, we could to look at a Kubernetes or Kafka type of system. Either of these solutions could be run on-prem or in the cloud. 

A description of what I have been working on for the on-prem option is show [here](https://github.com/derekcoffman/iot-data-landing/blob/bd6ef5a2189b89c2edb74067f1668cf0c0a3b7a5/docs/sandbox_k8s_setup.md)

One major question I need to get answered...what is the policy for data retention? Specifically, do we have to maintain a copy of data on-prem or does having data in cloud storage work just as well? Answered: if it's storage on NOAA's purchased commerical cloud it is considered NOAA IT infrastructure and does not need to be maintained on-prem. If the data are part of the Big Data Project, they do have to be maintained on-prem.