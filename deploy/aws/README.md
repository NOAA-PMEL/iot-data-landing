# AWS Deploy

## Create AWS Cluster

`eksctl`

## Integrate with `kubectl`

```shell
$ alias k=kubectl
$ export KUBECONFIG=$(k3d kubeconfig write iot-data-landing)
$ aws eks --profile iot-data-landing update-kubeconfig --region us-east-1 --name pmel-cluster-002

Added new context arn:aws:eks:us-east-1:514573433251:cluster/pmel-cluster-002 to /home/kwilcox/.k3d/kubeconfig-iot-data-landing.yaml
```

```shell
$ k get svc
NAME         TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
kubernetes   ClusterIP   10.100.0.1   <none>        443/TCP   161d
```

## Load balancer

<https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html>

## EBS Storage

https://docs.aws.amazon.com/eks/latest/userguide/managing-ebs-csi.html

More specfically:
* https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html
* https://docs.aws.amazon.com/eks/latest/userguide/csi-iam-role.html

## Install Strimizi or use MSK

### Strimizi

https://strimzi.io/quickstarts/

```shell
$ k create namespace kafka
$ k create -n kafka -f 'https://strimzi.io/install/latest?namespace=kafka'
$ k apply -n kafka -f deploy/aws/prod/02_kafka.yaml
$ k wait kafka/iot-cluster --for=condition=Ready --timeout=300s -n kafka

kafka.kafka.strimzi.io/iot-cluster condition met
```

### MSK

Create a new cluster and look for the TLS connection string:

`b-1.iotdatalandingkafka00.9bi4gz.c18.kafka.us-east-1.amazonaws.com:9094,b-2.iotdatalandingkafka00.9bi4gz.c18.kafka.us-east-1.amazonaws.com:9094`


## Knative

### Operator

```shell
$ k apply -f kubectl apply -f kubectl apply -f kubectl apply -f https://github.com/knative/operator/releases/download/knative-v1.8.1/operator.yaml
...
```

### Networking (Kong)

```shell
$ k apply -f https://raw.githubusercontent.com/Kong/kubernetes-ingress-controller/master/deploy/single/all-in-one-dbless.yaml
...

$ k get service kong-proxy -n kong
NAME         TYPE           CLUSTER-IP      EXTERNAL-IP                                                                     PORT(S)                      AGE
kong-proxy   LoadBalancer   10.100.159.15   adec8489763c849cc9cc86059dcef862-0530fee0bf7ccd40.elb.us-east-1.amazonaws.com   80:31572/TCP,443:30934/TCP   84s

$ export PROXY_IP=$(kubectl get -o jsonpath="{.status.loadBalancer.ingress[0].hostname}" service -n kong kong-proxy)
$ echo $PROXY_IP
adec8489763c849cc9cc86059dcef862-0530fee0bf7ccd40.elb.us-east-1.amazonaws.com

$ curl -i $PROXY_IP
HTTP/1.1 404 Not Found
Date: Mon, 14 Nov 2022 15:38:49 GMT
Content-Type: application/json; charset=utf-8
Connection: keep-alive
Content-Length: 48
X-Kong-Response-Latency: 0
Server: kong/3.0.1

{"message":"no Route matched with those values"}%
```

### Serving

```shell
$ k apply -f deploy/aws/prod/04_knative_serving.yaml
...

$ kubectl get KnativeServing knative-serving -n knative-serving
NAME              VERSION   READY   REASON
knative-serving   1.8.0     True
```

```shell
$ k apply -f deploy/aws/prod/05_knative_example.yaml
...

$ curl -i "http://$PROXY_IP" -H "Host: helloworld-go.default.$PROXY_IP"
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 25
Connection: keep-alive
Date: Mon, 14 Nov 2022 16:13:33 GMT
X-Kong-Upstream-Latency: 1
X-Kong-Proxy-Latency: 1
Via: kong/3.0.1

Hello  - It is Working!!
```

### Eventing

This secret needs to be created in AWS Secrets Manager and attached to the MSK instance with SASL authentication. Then you can make the Kafka brokers public. This needs a non-default KMS key (`iot-data-landing`). See https://docs.aws.amazon.com/msk/latest/developerguide/msk-password.html.

AmazonMSK_iot-data-landing-kafka-secret-03

```shell
$ k create secret --namespace knative-eventing generic iot-data-landing-kafka-secret \
  --from-literal=protocol=SASL_PLAINTEXT \
  --from-literal=sasl.mechanism=PLAIN \
  --from-literal=user=iot-data-landing-kafka-user \
  --from-literal=password=[password]
...
```

```shell
$ k apply -f deploy/aws/prod/06_knative_eventing.yaml
namespace/knative-eventing created
knativeeventing.operator.knative.dev/knative-eventing created

$ k apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.8.1/eventing-kafka-controller.yaml
...

$ k apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.8.1/eventing-kafka-broker.yaml
...

$ k apply -f deploy/aws/prod/07_knative_eventing_config.yaml
...

$ k get KnativeEventing knative-eventing -n knative-eventing
NAME               VERSION   READY   REASON
knative-eventing   1.8.0     True
```

Make sure the Kafka broker is ready to go!

```shell
$ kn broker list

NAME      URL                                                                              AGE    CONDITIONS   READY   REASON
default   http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default   4m4s   7 OK / 7     True
```
