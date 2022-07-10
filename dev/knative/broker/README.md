# Add Kafka broker

## Add controller
```
kubectl apply --filename https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.4.0/eventing-kafka-controller.yaml
```

## Add data plane
```
kubectl apply --filename https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.4.0/eventing-kafka-broker.yaml
```

## Create a Broker
Create the iot namespace
```
kubectl create namespace iot
```

The broker is defined for the k3d instance in dev/knative/broker: 
```
kubectl apply -f dev/knative/broker
```
To check if successful:
```
kubectl get broker -n iot
```
to make sure the broker is ready

NAME    URL

iot-default  http://kafka-broker-ingress.knative-eventing.svc.cluster.local/iot/iot-default

