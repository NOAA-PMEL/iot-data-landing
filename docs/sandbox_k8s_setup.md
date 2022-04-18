# Sandbox IoT Data Setup
In an effort to look at a vendor agnostic option, I have set up a on-prem Kubernetes cluster to test the IoT Data System. The system has the following components:
 - Management - [Rancher](https://rancher.com/products/rancher) running on first VM in sandbox (wallingford)
 - Kubernetes - single [k3s](https://rancher.com/products/k3s) cluster running on second VM in sandbox (roosevelt)
   - Serverless/Eventing - [Knative](https://knative.dev/docs/)
   - persistent messaging bus - Kafka using [Strimzi](https://strimzi.io/)
   - load balancer - [MetalLB](https://metallb.universe.tf/) because k8s does not provide load balancing out of the box
 - Data server - ERDDAP running on wallingford (non k8s machine) using axiom docker image 
 - MQTT broker - [Mosquitto](https://mosquitto.org/) using docker image 
 - Local container registry - [Harbor](https://goharbor.io/) running on wallingford to maintain local registry of docker images used by k8s/Knative
 - MQTT bridge - python app written by me to get data from MQTT broker and send to Knative broker

 ## Data flow
  - Mock sensor data source sends to MQTT broker. Data wrapped in cloudevent envelope. No encryption at this point.
  - MQTT Broker - data published to broker on instrument/data topic
  - MQTT Bridge - subscribed to instrument/data. On message (cloudevent) to Knative Kafka broker via http POST request. This is a python app that has been dockerized and running as a k8s pod. No scale to zero.
  - Knative Kafka broker - inject cloudevent into Knative system backed by Kafka
  - Knative Trigger - waits for cloudevent based on type that matches type sent by MQTT Bridge, sends to Knative service
  - Knative Service - "serverless" function that accepts cloudevent via http and parses data in payload. This data will then be sent to ERDDAP using HTTPGet dataset type.